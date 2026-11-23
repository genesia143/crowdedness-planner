"""Experimental mobile-ticket pressure, not measured bus occupancy."""
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import math
import sqlite3
from pathlib import Path
from model import day_type, normalize


@lru_cache(maxsize=200000)
def pressure(database, route, origin, destination, kind, hour):
    """Pool a three-hour window; fall back to the route if no segment evidence.

    Totals include scheduled days without matched tickets. The route fallback
    averages segment-occurrences and is not a reconstruction of individual trips.
    """
    with sqlite3.connect('file:' + str(Path(database).resolve()) + '?mode=ro', uri=True) as db:
        def get(segment):
            condition = ' AND t.origin=? AND t.destination=?' if segment else ''
            args = (route, kind, max(0, hour - 1), min(23, hour + 1))
            if segment:
                args += (origin, destination)
            return db.execute('''SELECT COALESCE(SUM(s.sampled_passengers),0), SUM(t.scheduled_crossings)
                FROM scheduled_totals t LEFT JOIN service_signals s
                ON s.route=t.route AND s.origin=t.origin AND s.destination=t.destination
                AND s.hour=t.hour AND s.day_type=t.day_type
                WHERE t.route=? AND t.day_type=? AND t.hour BETWEEN ? AND ?''' + condition, args).fetchone()
        passengers, crossings = get(True) if origin and destination else (0, 0)
        tier = 'segment_window'
        if not passengers or not crossings:
            passengers, crossings = route_pressure(db, route, kind, hour)
            tier = 'route_window'
        if not passengers or not crossings:
            passengers, crossings = _route_broad(str(Path(database).resolve()), route, kind)
            tier = 'route_day'
        if not passengers or not crossings:
            passengers, crossings = _route_broad(str(Path(database).resolve()), route, None)
            tier = 'route_all_days'
        if not passengers or not crossings:
            return None
        return {'score': passengers / crossings, 'tier': tier, 'sample_passengers': passengers}


@lru_cache(maxsize=10000)
def _route_pressure(database, route, kind, hour):
    with sqlite3.connect('file:' + str(Path(database).resolve()) + '?mode=ro', uri=True) as db:
        return db.execute('''SELECT COALESCE(SUM(s.sampled_passengers),0),SUM(t.scheduled_crossings)
            FROM scheduled_totals t LEFT JOIN service_signals s
            ON s.route=t.route AND s.origin=t.origin AND s.destination=t.destination
            AND s.hour=t.hour AND s.day_type=t.day_type
            WHERE t.route=? AND t.day_type=? AND t.hour BETWEEN ? AND ?''',
            (route, kind, max(0,hour-1), min(23,hour+1))).fetchone()


def route_pressure(db, route, kind, hour):
    path = db.execute('PRAGMA database_list').fetchone()[2]
    return _route_pressure(path, route, kind, hour)


@lru_cache(maxsize=5000)
def _route_broad(database, route, kind):
    with sqlite3.connect('file:' + str(Path(database).resolve()) + '?mode=ro', uri=True) as db:
        where = ' AND t.day_type=?' if kind else ''
        args = (route, kind) if kind else (route,)
        return db.execute('''SELECT COALESCE(SUM(s.sampled_passengers),0),SUM(t.scheduled_crossings)
            FROM scheduled_totals t LEFT JOIN service_signals s
            ON s.route=t.route AND s.origin=t.origin AND s.destination=t.destination
            AND s.hour=t.hour AND s.day_type=t.day_type WHERE t.route=?''' + where, args).fetchone()


def estimate(journey, database):
    if not database:
        return {'status': 'unavailable', 'reason': 'Model database is unavailable'}
    legs = [leg for leg in journey.get('legs', []) if leg.get('mode') == 'BUS']
    weighted, total, tiers, missing, support = 0.0, 0.0, set(), 0, []
    for leg in legs:
        route = normalize((leg.get('route') or {}).get('shortName') or '')
        signals = leg.get('v1_signals') or []
        try:
            duration = float(leg.get('duration_minutes'))
            moment = datetime.fromisoformat((leg.get('start') or {})['scheduledTime'].replace('Z', '+00:00'))
            if not route or not math.isfinite(duration) or duration <= 0 or moment.utcoffset() is None:
                raise ValueError('missing route or time')
            moment = moment.astimezone(timezone(timedelta(hours=5, minutes=30)))
        except (ValueError, TypeError, KeyError, AttributeError):
            missing += 1
            continue
        estimates = []
        for signal in signals or [{}]:
            sample = pressure(database, route, signal.get('from_stop_id'), signal.get('to_stop_id'), day_type(moment), moment.hour)
            if sample:
                estimates.append(sample)
        if not estimates:
            missing += 1
            continue
        weighted += duration * sum(x['score'] for x in estimates) / len(estimates)
        total += duration
        tiers.update(x['tier'] for x in estimates)
        support.extend(x['sample_passengers'] for x in estimates)
    if not legs or missing or not total:
        return {'status': 'unavailable', 'reason': 'One or more bus legs have no usable evidence', 'missing_legs': missing}
    return {'status': 'available', 'score': weighted / total, 'evidence_tiers': sorted(tiers),
            'minimum_pool_passengers': min(support),
            'assumption': 'Uniform mobile-ticket uptake across routes; GTFS scheduled buses approximate service. Wider route, time and day fallbacks are provisional, not actual loads.'}


def compare(journeys, eligible, database):
    for i in eligible:
        journeys[i]['journey_pressure'] = estimate(journeys[i], database)
    for i in eligible:
        result = journeys[i]['journey_pressure']
        if result['status'] != 'available':
            continue
        score = result['score']
        # Fixed, exploratory cutoffs from training-period segment-hour quantiles;
        # not calibrated to people onboard, seats, capacity, or journey scores.
        result['label'] = ('Low estimated crowding' if score < 1/6 else
                           'Moderate estimated crowding' if score < 0.4 else
                           'High estimated crowding')
        result['label_basis'] = 'Fixed exploratory training-sample pressure bands; not calibrated occupancy or seating.'
