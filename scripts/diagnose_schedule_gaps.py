"""Diagnose tuning-sample segment hours against the static timetable.

This is a timing diagnostic, not an occupancy validation. It reads only a
previously built October 22–24 tuning artifact and refuses other periods.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from service import scheduled_crossings


def diagnose(data, schedule):
    start, end = data['training_start'], data['training_end']
    if start < '2026-10-22' or end > '2026-10-24' or end < start:
        raise ValueError('diagnostic is restricted to October 22–24, 2026')
    observed = Counter()
    for row in data['records']:
        if not start <= row['date'] <= end:
            raise ValueError('record outside declared tuning dates')
        observed[(row['route'], row['from_stop_id'], row['to_stop_id'],
                  row['date'], row['hour'], row['day_type'])] += row['passengers']
    hours = defaultdict(set)
    for route, origin, dest, day, hour, kind in schedule:
        hours[(route, origin, dest, day, kind)].add(hour)
    result = defaultdict(lambda: {'cells': 0, 'sample_passenger_segment_records': 0})
    for (route, origin, dest, day, hour, kind), passengers in observed.items():
        available = hours[(route, origin, dest, day, kind)]
        if hour in available:
            group = 'same_hour'
        elif hour - 1 in available and hour + 1 in available:
            group = 'adjacent_both'
        elif hour - 1 in available:
            group = 'previous_hour_only'
        elif hour + 1 in available:
            group = 'next_hour_only'
        elif available:
            group = 'other_hour_same_day'
        else:
            group = 'no_crossing_same_day'
        result[group]['cells'] += 1
        result[group]['sample_passenger_segment_records'] += passengers
    return dict(result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validation', required=True)
    parser.add_argument('--gtfs', required=True)
    args = parser.parse_args()
    with open(args.validation, encoding='utf-8') as handle:
        data = json.load(handle)
    start, end = data['training_start'], data['training_end']
    if start < '2026-10-22' or end > '2026-10-24' or end < start:
        raise ValueError('diagnostic is restricted to October 22–24, 2026')
    print(json.dumps(diagnose(data, scheduled_crossings(args.gtfs, start, end)), indent=2))
