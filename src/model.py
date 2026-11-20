"""Conservative ticket-derived segment signal; Python standard library only."""
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path


def normalize(value):
    return re.sub(r'[^a-z0-9]+', ' ', (value or '').lower()).strip()


def rows(path):
    with open(path, encoding='utf-8-sig', newline='') as handle:
        yield from csv.DictReader(handle)


def route_patterns(gtfs):
    gtfs = Path(gtfs)
    names = {r['stop_id']: r['stop_name'] for r in rows(gtfs / 'stops.txt')}
    routes = {r['route_id']: r['route_short_name'] for r in rows(gtfs / 'routes.txt')}
    trips = {r['trip_id']: routes.get(r['route_id']) for r in rows(gtfs / 'trips.txt')}
    stops = defaultdict(list)
    for row in rows(gtfs / 'stop_times.txt'):
        if row['trip_id'] in trips and row['stop_id'] in names:
            stops[row['trip_id']].append((int(row['stop_sequence']), row['stop_id']))
    patterns = defaultdict(set)
    for trip, sequence in stops.items():
        route = trips[trip]
        if route:
            patterns[normalize(route)].add(tuple(stop for _, stop in sorted(sequence)))
    return names, patterns


def match_segments(route, start, end, names, patterns):
    candidates = set()
    for pattern in patterns.get(normalize(route), ()):
        for i, stop in enumerate(pattern):
            if normalize(names[stop]) != normalize(start):
                continue
            for j in range(i + 1, len(pattern)):
                if normalize(names[pattern[j]]) == normalize(end):
                    candidates.add(tuple(zip(pattern[i:j], pattern[i+1:j+1])))
    return next(iter(candidates)) if len(candidates) == 1 else None


def build(tickets, gtfs, start_date, end_date, output):
    start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
    if end < start:
        raise ValueError('end date must not precede start date')
    names, patterns = route_patterns(gtfs)
    counts, quality, cache = Counter(), Counter(), {}
    for row in rows(tickets):
        try:
            timestamp = datetime.fromisoformat(row['created_at'])
            if timestamp.utcoffset() is None:
                raise ValueError('timestamp must include an offset')
            # Ticket timestamps in this dataset are in IST. Normalize offsets before assigning the date.
            from datetime import timedelta, timezone
            timestamp = timestamp.astimezone(timezone(timedelta(hours=5, minutes=30)))
            if not start <= timestamp.date() <= end:
                continue
            passengers = int(row['passenger_count'])
            if passengers <= 0:
                raise ValueError('passenger count must be positive')
        except (KeyError, TypeError, ValueError):
            quality['invalid_date_or_count'] += 1
            continue
        quality['in_period'] += 1
        key = (row.get('route', ''), row.get('start_stop_name', ''), row.get('end_stop_name', ''))
        if key not in cache:
            cache[key] = match_segments(*key, names, patterns)
        segments = cache[key]
        if not segments:
            quality['unmatched_or_ambiguous'] += 1
            continue
        quality['matched'] += 1
        day_type = 'weekend' if timestamp.weekday() >= 5 else 'weekday'
        for a, b in segments:
            counts[(normalize(key[0]), a, b, timestamp.date().isoformat(), timestamp.hour, day_type)] += passengers
    result = {'definition': 'observed ticket-sample passenger journeys crossing a segment, grouped by ticket boarding hour',
              'training_start': start_date, 'training_end': end_date, 'quality': dict(quality),
              'records': [{'route': route, 'from_stop_id': a, 'to_stop_id': b, 'date': day,
                           'hour': hour, 'day_type': kind, 'passengers': value}
                          for (route, a, b, day, hour, kind), value in sorted(counts.items())]}
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    with open(output, 'w', encoding='utf-8') as handle:
        json.dump(result, handle)
    return result
