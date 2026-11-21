"""GTFS scheduled segment crossings, including calendar exceptions and >24h times."""
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from model import day_type, normalize, rows


def active_services(gtfs, start, end):
    gtfs = Path(gtfs)
    active = defaultdict(set)
    calendar = gtfs / 'calendar.txt'
    if calendar.exists():
        for row in rows(calendar):
            first = datetime.strptime(row['start_date'], '%Y%m%d').date()
            last = datetime.strptime(row['end_date'], '%Y%m%d').date()
            day = max(start, first)
            while day <= min(end, last):
                if row[['monday','tuesday','wednesday','thursday','friday','saturday','sunday'][day.weekday()]] == '1':
                    active[day].add(row['service_id'])
                day += timedelta(days=1)
    exceptions = gtfs / 'calendar_dates.txt'
    if exceptions.exists():
        for row in rows(exceptions):
            day = datetime.strptime(row['date'], '%Y%m%d').date()
            if start <= day <= end:
                if row['exception_type'] == '1':
                    active[day].add(row['service_id'])
                elif row['exception_type'] == '2':
                    active[day].discard(row['service_id'])
    if not calendar.exists() and not exceptions.exists():
        raise ValueError('GTFS feed has no service calendar')
    return active


def scheduled_crossings(gtfs, start, end):
    gtfs = Path(gtfs)
    start, end = date.fromisoformat(start), date.fromisoformat(end)
    if end < start:
        raise ValueError('end before start')
    if (gtfs / 'frequencies.txt').exists():
        raise ValueError('frequency-based GTFS service is not supported yet')
    # Previous service day may contain trips with times after midnight.
    active = active_services(gtfs, start - timedelta(days=1), end)
    route_names = {r['route_id']: normalize(r['route_short_name']) for r in rows(gtfs / 'routes.txt')}
    trips = {r['trip_id']: (route_names.get(r['route_id']), r['service_id']) for r in rows(gtfs / 'trips.txt')}
    stop_times = defaultdict(list)
    for row in rows(gtfs / 'stop_times.txt'):
        if row['trip_id'] in trips:
            stop_times[row['trip_id']].append((int(row['stop_sequence']), row['stop_id'], row['departure_time']))
    counts = Counter()
    for trip, sequence in stop_times.items():
        route, service = trips[trip]
        if not route:
            continue
        sequence.sort()
        for first, second in zip(sequence, sequence[1:]):
            parts = first[2].split(':')
            if len(parts) != 3:
                raise ValueError('missing or invalid scheduled departure time')
            h, m, s = map(int, parts)
            if not 0 <= h < 48 or not 0 <= m < 60 or not 0 <= s < 60:
                raise ValueError('invalid scheduled departure time')
            for service_day, services in active.items():
                if service not in services:
                    continue
                actual_day = service_day + timedelta(days=h // 24)
                if start <= actual_day <= end:
                    kind = day_type(actual_day)
                    counts[(route, first[1], second[1], actual_day.isoformat(), h % 24, kind)] += 1
    return counts
