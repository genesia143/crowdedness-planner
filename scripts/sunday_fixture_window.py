"""Measure experimental three-hour Sunday coverage on a recorded API response."""
import argparse
import collections
import json
import re
import sqlite3
from datetime import datetime

SUNDAYS = ('2026-10-04', '2026-10-11', '2026-10-18')


def normalize(value):
    return re.sub(r'[^a-z0-9]+', ' ', (value or '').lower()).strip()


def signal_for_window(key, hour, sample, scheduled, radius=1, min_days=2, min_pax=5):
    """Return evidence support for a candidate, not a validated model label."""
    eligible = {}
    for h in range(24):
        if not scheduled.get(key + (h,), 0):
            continue
        window = range(max(0, h-radius), min(23, h+radius)+1)
        crossings = sum(scheduled.get(key + (x,), 0) for x in window)
        daily = [sum(sample.get(key + (x, date), 0) for x in window) for date in SUNDAYS]
        if crossings and sum(v > 0 for v in daily) >= min_days and sum(daily) >= min_pax:
            eligible[h] = sum(daily) / crossings
    return hour in eligible and len(eligible) >= 3 and len(set(eligible.values())) >= 2


def main(records, database, fixture):
    response = json.load(open(fixture, encoding='utf-8'))['body']
    legs = [leg for journey in response['journeys'] for leg in journey['legs'] if leg.get('mode') == 'BUS']
    queries = []
    for leg in legs:
        route = normalize(leg['route']['shortName'])
        queries.append([(route, str(s['from_stop_id']), str(s['to_stop_id']), datetime.fromisoformat(s['model_lookup_time']).hour) for s in leg.get('v1_signals', [])])
    keys = {q[:3] for leg in queries for q in leg}
    source = json.load(open(records, encoding='utf-8'))
    if (source['training_start'], source['training_end']) != ('2026-10-01', '2026-10-21'):
        raise ValueError('Requires original training records')
    sample = collections.defaultdict(int)
    for r in source['records']:
        key = (r['route'], r['from_stop_id'], r['to_stop_id'])
        if key in keys and r['date'] in SUNDAYS:
            sample[key + (r['hour'], r['date'])] += r['passengers']
    del source
    db = sqlite3.connect(f'file:{database}?mode=ro', uri=True)
    schedule = {}
    for route, a, b, hour, days, crossings in db.execute("SELECT route,origin,destination,hour,scheduled_days,scheduled_crossings FROM scheduled_totals WHERE day_type='sunday'"):
        if (route, a, b) in keys and days == 3 and crossings > 0:
            schedule[(route, a, b, hour)] = crossings
    db.close()
    counts = [sum(signal_for_window(q[:3], q[3], sample, schedule) for q in leg) for leg in queries]
    return {'journeys': len(response['journeys']), 'bus_legs': len(legs), 'bus_segments': sum(map(len, queries)), 'segments_supported': sum(counts), 'legs_with_any_supported': sum(x > 0 for x in counts), 'legs_with_all_supported': sum(bool(q) and c == len(q) for q, c in zip(queries, counts)), 'per_leg_supported': counts, 'caveats': 'Training-only exploratory 3-hour support with at least 2 observed Sundays and 5 sample passengers. No classification accuracy established, no occupancy claim. Repeated route segments in different journeys count repeatedly.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--records', required=True)
    parser.add_argument('--database', required=True)
    parser.add_argument('--fixture', required=True)
    args = parser.parse_args()
    print(json.dumps(main(args.records, args.database, args.fixture), indent=2))
