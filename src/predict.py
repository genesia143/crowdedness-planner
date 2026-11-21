"""Compact descriptive baseline and its query logic; not a crowding model."""
import json
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def model_timing_basis(database):
    """Determine the indexed time convention; refuse unknown metadata."""
    with sqlite3.connect('file:' + str(Path(database).resolve()) + '?mode=ro', uri=True) as db:
        row = db.execute("SELECT value FROM metadata WHERE key='definition'").fetchone()
    definition = json.loads(row[0]) if row else ''
    if 'estimated segment crossing hour' in definition:
        return 'crossing'
    if 'grouped by ticket boarding hour' in definition:
        return 'boarding'
    raise ValueError('Model timing convention is unknown; rebuild the model')


def relative_band(db, route, origin, destination, day_type, hour):
    """Provisional within-segment time-of-day rank, using training data only.

    This deliberately does not compare different segments or routes: ticket
    uptake may differ between them. Thresholds are initial support rules, not
    measured confidence or calibrated passenger occupancy.
    """
    unavailable = {'label': 'insufficient evidence', 'provisional': True,
                   'comparison': 'same route, directed segment and day type across hours',
                   'reason': 'too few supported hours or observations for a relative comparison'}
    has_totals = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='scheduled_totals'").fetchone()
    if not has_totals:
        return unavailable
    rows = db.execute('''SELECT s.hour, s.matched_days, s.sampled_passengers,
                                t.scheduled_days, t.scheduled_crossings
                         FROM service_signals s JOIN scheduled_totals t
                         ON s.route=t.route AND s.origin=t.origin AND s.destination=t.destination
                         AND s.hour=t.hour AND s.day_type=t.day_type
                         WHERE s.route=? AND s.origin=? AND s.destination=? AND s.day_type=?''',
                      (route, origin, destination, day_type)).fetchall()
    supported = {h: passengers / crossings for h, days, passengers, scheduled_days, crossings in rows
                 if days >= 3 and passengers >= 10 and scheduled_days >= 4 and crossings > 0}
    if hour not in supported or len(supported) < 3 or len(set(supported.values())) < 2:
        return unavailable
    value = supported[hour]
    # Midrank handles ties consistently, including all members of a tie.
    percentile = (sum(v < value for v in supported.values()) +
                  0.5 * sum(v == value for v in supported.values())) / len(supported)
    label = 'likely quieter' if percentile < 1 / 3 else 'likely busier' if percentile > 2 / 3 else 'typical'
    return {'label': label, 'provisional': True,
            'comparison': 'same route, directed segment and day type across hours',
            'relative_percentile': percentile, 'reference_hours': len(supported),
            'limitation': 'Ticket-sample pressure per scheduled crossing; not actual crowding, occupancy, or a cross-route comparison. Thresholds are not yet validated.'}


def create_database(source, destination, gtfs=None):
    with open(source, encoding='utf-8') as handle:
        data = json.load(handle)
    from service import scheduled_crossings
    scheduled = scheduled_crossings(gtfs, data['training_start'], data['training_end']) if gtfs else None
    db = sqlite3.connect(destination)
    try:
        db.execute('DROP TABLE IF EXISTS signals')
        db.execute('DROP TABLE IF EXISTS metadata')
        db.execute('DROP TABLE IF EXISTS service_signals')
        db.execute('DROP TABLE IF EXISTS scheduled_totals')
        db.execute('CREATE TABLE signals (route TEXT, origin TEXT, destination TEXT, hour INTEGER, day_type TEXT, observed_days INTEGER, total INTEGER, PRIMARY KEY(route,origin,destination,hour,day_type))')
        db.execute('CREATE TABLE service_signals (route TEXT, origin TEXT, destination TEXT, hour INTEGER, day_type TEXT, matched_days INTEGER, sampled_passengers INTEGER, scheduled_crossings INTEGER, unmatched_days INTEGER, PRIMARY KEY(route,origin,destination,hour,day_type))')
        db.execute('CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT)')
        db.execute('CREATE TABLE scheduled_totals (route TEXT, origin TEXT, destination TEXT, hour INTEGER, day_type TEXT, scheduled_days INTEGER, scheduled_crossings INTEGER, PRIMARY KEY(route,origin,destination,hour,day_type))')
        schedule_totals = defaultdict(lambda: [0, 0])
        if scheduled is not None:
            for (route, origin, dest, day, hour, kind), buses in scheduled.items():
                entry = schedule_totals[(route, origin, dest, hour, kind)]
                entry[0] += 1
                entry[1] += buses
        db.executemany('INSERT INTO scheduled_totals VALUES (?,?,?,?,?,?,?)', (key + tuple(value) for key, value in schedule_totals.items()))
        summaries = defaultdict(lambda: [0, 0])
        service_summaries = defaultdict(lambda: [0, 0, 0, 0])
        for row in data['records']:
            key = (row['route'], row['from_stop_id'], row['to_stop_id'], row['hour'], row['day_type'])
            summaries[key][0] += 1
            summaries[key][1] += row['passengers']
            if scheduled is not None:
                day_key = (row['route'], row['from_stop_id'], row['to_stop_id'], row['date'], row['hour'], row['day_type'])
                buses = scheduled.get(day_key, 0)
                values = service_summaries[key]
                if buses:
                    values[0] += 1
                    values[1] += row['passengers']
                    values[2] += buses
                else:
                    values[3] += 1
        db.executemany('INSERT INTO signals VALUES (?,?,?,?,?,?,?)', (key + tuple(value) for key, value in summaries.items()))
        db.executemany('INSERT INTO service_signals VALUES (?,?,?,?,?,?,?,?,?)', (key + tuple(value) for key, value in service_summaries.items()))
        db.executemany('INSERT INTO metadata VALUES (?,?)', [(key, json.dumps(data[key])) for key in ('training_start','training_end','definition','quality')])
        db.commit()
    finally:
        db.close()


def query(database, route, origin, destination, departure):
    from model import normalize, parse_timestamp
    timestamp = parse_timestamp(departure)
    if timestamp.utcoffset() is None:
        raise ValueError('departure must include a timezone offset')
    from datetime import timedelta, timezone
    timestamp = timestamp.astimezone(timezone(timedelta(hours=5, minutes=30)))
    kind = 'weekend' if timestamp.weekday() >= 5 else 'weekday'
    if not Path(database).is_file():
        raise FileNotFoundError('model database not found')
    with sqlite3.connect('file:' + str(Path(database).resolve()) + '?mode=ro', uri=True) as db:
        row = db.execute('SELECT observed_days,total FROM signals WHERE route=? AND origin=? AND destination=? AND hour=? AND day_type=?', (normalize(route),origin,destination,timestamp.hour,kind)).fetchone()
        service = db.execute('SELECT matched_days,sampled_passengers,scheduled_crossings,unmatched_days FROM service_signals WHERE route=? AND origin=? AND destination=? AND hour=? AND day_type=?', (normalize(route),origin,destination,timestamp.hour,kind)).fetchone()
        has_totals = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='scheduled_totals'").fetchone()
        totals = db.execute('SELECT scheduled_days,scheduled_crossings FROM scheduled_totals WHERE route=? AND origin=? AND destination=? AND hour=? AND day_type=?', (normalize(route),origin,destination,timestamp.hour,kind)).fetchone() if has_totals else None
        metadata = {key: json.loads(value) for key, value in db.execute('SELECT key,value FROM metadata')}
        band = relative_band(db, normalize(route), origin, destination, kind, timestamp.hour)
    alignment = None
    if row is not None and service is not None:
        observed_total = row[1]
        included = service[1]
        alignment = {'matched_sample_passenger_segments': observed_total,
                     'included_with_same_hour_service': included,
                     'excluded_without_same_hour_service': observed_total - included,
                     'excluded_sample_fraction': (observed_total - included) / observed_total if observed_total else None,
                     'days_with_unmatched_service': service[3],
                     'interpretation': 'Matched ticket sample for this route, directed segment, hour and day type during training; schedule mismatch may reflect timing or service differences. Not a share of all riders.'}
    if row is None:
        assumed = None
        if totals and totals[1]:
            assumed = {'sample_passengers_per_scheduled_crossing': 0.0, 'sample_passengers': 0, 'scheduled_days': totals[0], 'scheduled_crossings': totals[1], 'observed_days_with_schedule': 0, 'assumption': 'Zero matched ticket records on scheduled days; valid as a sample count only if ticket ingestion was complete, and not evidence of zero actual riders.'}
        return {'status': 'unavailable', 'reason': 'no matched sample observations for this segment and time', 'all_scheduled_days_proxy': assumed, 'relative_crowding': band, 'schedule_alignment': alignment, 'training': metadata}
    days, total = row
    normalized = None
    if service and service[2]:
        normalized = {'sample_passengers_per_scheduled_crossing': service[1] / service[2], 'matched_days': service[0], 'sample_passengers': service[1], 'scheduled_crossings': service[2], 'days_without_matching_schedule': service[3], 'limitation': 'Only days with matched ticket observations and scheduled crossings. Timing depends on the training method; scheduled service may differ from actual service.'}
    all_days = None
    if service and totals and totals[1]:
        all_days = {'sample_passengers_per_scheduled_crossing': service[1] / totals[1], 'sample_passengers': service[1], 'scheduled_days': totals[0], 'scheduled_crossings': totals[1], 'observed_days_with_schedule': service[0], 'days_without_matching_schedule': service[3], 'assumption': 'Days with scheduled service but no matched ticket observations are counted as zero observed tickets; incomplete ticket coverage can bias this value.'}
    return {'status': 'available', 'scheduled_service_proxy': normalized, 'all_scheduled_days_proxy': all_days, 'relative_crowding': band, 'schedule_alignment': alignment, 'sample_passengers_per_observed_day': total / days, 'observed_days': days,
            'definition': 'Mean ticket-sample passenger crossings on days with at least one matched ticket. Not occupancy or per-bus load. Timing: ' + metadata['definition'],
            'day_type': kind, 'hour_ist': timestamp.hour, 'training': metadata}
