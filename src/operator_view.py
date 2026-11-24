"""Operator view: stretches and routes with the highest mobile-ticket pressure.

Pressure is matched mobile-ticket passengers per scheduled bus crossing over
the chosen day type and hours, using the same training totals as the journey
estimate (days with a scheduled crossing but no matched ticket count as zero).
Ranking across routes assumes similar mobile-ticket uptake on every route; it
indicates where to look first, not measured occupancy.
"""
import sqlite3
from functools import lru_cache
from pathlib import Path
from model import normalize, rows

DAY_TYPES = ('weekday', 'saturday', 'sunday')
BASIS = ('Matched mobile-ticket passengers per scheduled bus crossing, 1-21 October 2026 training data. '
         'Ranking across routes assumes similar mobile-ticket use on every route; it is an indication of where '
         'to look first, not a count of people on board.')


@lru_cache(maxsize=4)
def route_names(gtfs):
    return {normalize(r['route_short_name']): r['route_short_name'] for r in rows(Path(gtfs) / 'routes.txt')}


def validate(day_type, hour_from, hour_to, limit, min_sample):
    if day_type not in DAY_TYPES:
        raise ValueError('day_type must be weekday, saturday or sunday')
    try:
        hour_from, hour_to, limit, min_sample = int(hour_from), int(hour_to), int(limit), int(min_sample)
    except (TypeError, ValueError):
        raise ValueError('hours, limit and min_sample must be whole numbers')
    if not 0 <= hour_from <= hour_to <= 23:
        raise ValueError('hours must satisfy 0 <= hour_from <= hour_to <= 23')
    if not 1 <= limit <= 100:
        raise ValueError('limit must be between 1 and 100')
    if not 1 <= min_sample <= 10000:
        raise ValueError('min_sample must be between 1 and 10000')
    return day_type, hour_from, hour_to, limit, min_sample


@lru_cache(maxsize=64)
def _ranked(database, day_type, hour_from, hour_to, min_sample):
    with sqlite3.connect('file:' + str(Path(database).resolve()) + '?mode=ro', uri=True) as db:
        segments = db.execute('''SELECT t.route, t.origin, t.destination, SUM(t.scheduled_crossings) AS crossings,
                                        COALESCE(SUM(s.sampled_passengers), 0) AS passengers
                                 FROM scheduled_totals t LEFT JOIN service_signals s USING(route, origin, destination, hour, day_type)
                                 WHERE t.day_type=? AND t.hour BETWEEN ? AND ?
                                 GROUP BY t.route, t.origin, t.destination
                                 HAVING passengers >= ? AND crossings > 0
                                 ORDER BY 1.0 * passengers / crossings DESC, t.route, t.origin''',
                              (day_type, hour_from, hour_to, min_sample)).fetchall()
        routes = db.execute('''SELECT t.route, SUM(t.scheduled_crossings) AS crossings, COALESCE(SUM(s.sampled_passengers), 0) AS passengers
                               FROM scheduled_totals t LEFT JOIN service_signals s USING(route, origin, destination, hour, day_type)
                               WHERE t.day_type=? AND t.hour BETWEEN ? AND ?
                               GROUP BY t.route HAVING passengers >= ? AND crossings > 0
                               ORDER BY 1.0 * passengers / crossings DESC, t.route''',
                            (day_type, hour_from, hour_to, min_sample)).fetchall()
    return tuple(segments), tuple(routes)


def busiest(database, stops, coordinates, names, day_type='weekday', hour_from=8, hour_to=9, limit=25, min_sample=20):
    day_type, hour_from, hour_to, limit, min_sample = validate(day_type, hour_from, hour_to, limit, min_sample)
    segments, routes = _ranked(str(Path(database).resolve()), day_type, hour_from, hour_to, min_sample)
    def place(stop):
        lat, lon = coordinates.get(stop, (None, None))
        return {'stop_id': stop, 'name': stops.get(stop, ''), 'lat': lat, 'lon': lon}
    return {
        'day_type': day_type, 'hour_from': hour_from, 'hour_to': hour_to, 'min_sample': min_sample,
        'stretches': [{'route': names.get(route, route), 'from': place(a), 'to': place(b),
                       'pressure': passengers / crossings, 'sample_passengers': passengers, 'scheduled_crossings': crossings}
                      for route, a, b, crossings, passengers in segments[:limit]],
        'routes': [{'route': names.get(route, route), 'pressure': passengers / crossings,
                    'sample_passengers': passengers, 'scheduled_crossings': crossings}
                   for route, crossings, passengers in routes[:limit]],
        'qualifying_stretches': len(segments), 'qualifying_routes': len(routes),
        'basis': BASIS,
    }
