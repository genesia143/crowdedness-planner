"""Exploratory leave-one-Sunday-out evaluation; never reads final-week tickets."""
import argparse
import collections
import itertools
import json
import sqlite3

SUNDAYS = ('2026-10-04', '2026-10-11', '2026-10-18')


def evaluate(records_path, database):
    with open(records_path, encoding='utf-8') as f:
        data = json.load(f)
    if data['training_start'] != '2026-10-01' or data['training_end'] != '2026-10-21':
        raise ValueError('Requires the original October 1–21 training records')
    sample = collections.defaultdict(int)
    for r in data['records']:
        if r['date'] in SUNDAYS:
            sample[(r['route'], r['from_stop_id'], r['to_stop_id'], r['hour'], r['date'])] += r['passengers']
    del data
    conn = sqlite3.connect(f'file:{database}?mode=ro', uri=True)
    schedule = {}
    for route, a, b, hour, days, crossings in conn.execute("SELECT route, origin, destination, hour, scheduled_days, scheduled_crossings FROM scheduled_totals WHERE day_type='sunday'"):
        # The comparison is valid only for a consistent schedule across the three Sundays.
        if days == 3 and crossings > 0 and crossings % 3 == 0:
            schedule[(route, a, b, hour)] = crossings / 3
    conn.close()
    groups = collections.defaultdict(set)
    for route, a, b, hour in schedule:
        groups[(route, a, b)].add(hour)
    output = {}
    for radius in (0, 1):
        for minimum_days, minimum_pax in ((2, 5), (1, 3)):
            report = {'available_target_pax_segments': 0, 'covered_target_pax_segments': 0,
                      'supported_cells': 0, 'decisive_pairs': 0, 'concordant_pairs': 0,
                      'target_tie_pairs': 0, 'train_tie_pairs': 0}
            for held in SUNDAYS:
                train = [d for d in SUNDAYS if d != held]
                for key, hours in groups.items():
                    # Coverage denominator refers to actual target hour, not overlapping windows.
                    report['available_target_pax_segments'] += sum(sample[key + (h, held)] for h in hours)
                    points = []
                    for h in hours:
                        window = [x for x in range(max(0, h-radius), min(23, h+radius)+1) if x in hours]
                        crossings = sum(schedule[key + (x,)] for x in window)
                        if not crossings:
                            continue
                        values = [sum(sample[key + (x, day)] for x in window) for day in train]
                        if sum(v > 0 for v in values) < minimum_days or sum(values) < minimum_pax:
                            continue
                        prediction = sum(values) / (2 * crossings)
                        # All variants predict the same unsmoothed target hour.
                        target = sample[key + (h, held)] / schedule[key + (h,)]
                        points.append((h, prediction, target))
                    if len(points) < 3 or len({p[1] for p in points}) < 2:
                        continue
                    report['supported_cells'] += len(points)
                    report['covered_target_pax_segments'] += sum(sample[key + (p[0], held)] for p in points)
                    for a, b in itertools.combinations(points, 2):
                        x, y = a[1] - b[1], a[2] - b[2]
                        if x == 0:
                            report['train_tie_pairs'] += 1
                        elif y == 0:
                            report['target_tie_pairs'] += 1
                        else:
                            report['decisive_pairs'] += 1
                            report['concordant_pairs'] += int(x * y > 0)
            report['coverage'] = report['covered_target_pax_segments'] / report['available_target_pax_segments'] if report['available_target_pax_segments'] else None
            report['pair_agreement'] = report['concordant_pairs'] / report['decisive_pairs'] if report['decisive_pairs'] else None
            output[f'radius_{radius}_days_{minimum_days}_pax_{minimum_pax}'] = report
    return {'folds': SUNDAYS, 'variants': output, 'caveats': 'Ticket sample, not true occupancy; schedule counts assume same service on each Sunday. Wider training windows overlap, creating correlated predictions. All predictions compare against the unsmoothed target hour. Variants cover different populations; agreement is not a controlled improvement. Zero target counts assume complete ingestion. Boarding hour used for entire trip. Training-period selection, not final evaluation.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--records', required=True)
    p.add_argument('--database', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    result = evaluate(args.records, args.database)
    with open(args.output, 'x', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
