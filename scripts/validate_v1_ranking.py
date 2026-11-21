"""Compare supported within-segment hourly rankings with tuning-period tickets.

Development only: refuses data outside 22–24 October. A sample zero means no
matched ticket, not no riders. This is not validation against bus occupancy.
"""
import argparse
from collections import Counter, defaultdict
from itertools import combinations
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from service import scheduled_crossings


def compare_group(training, observed):
    """Compare distinct-hour pairs, treating target ties separately."""
    out = Counter()
    for a, b in combinations(sorted(set(training) & set(observed)), 2):
        train_diff = training[a] - training[b]
        target_diff = observed[a] - observed[b]
        out['hour_pairs'] += 1
        if train_diff == 0:
            out['training_ties'] += 1
        elif target_diff == 0:
            out['target_ties'] += 1
        elif train_diff * target_diff > 0:
            out['concordant'] += 1
        else:
            out['discordant'] += 1
    return out


def evaluate(database, validation, gtfs):
    with open(validation, encoding='utf-8') as handle:
        data = json.load(handle)
    start, end = data['training_start'], data['training_end']
    if start < '2026-10-22' or end > '2026-10-24' or end < start:
        raise ValueError('development evaluation is restricted to October 22–24, 2026')
    training = defaultdict(dict)
    with sqlite3.connect('file:' + str(Path(database).resolve()) + '?mode=ro', uri=True) as db:
        meta = {key: json.loads(value) for key, value in db.execute('SELECT key,value FROM metadata')}
        if meta['training_end'] >= start:
            raise ValueError('training must end before the evaluation period')
        sql = '''SELECT s.route,s.origin,s.destination,s.day_type,s.hour,
                        s.sampled_passengers,t.scheduled_crossings
                 FROM service_signals s JOIN scheduled_totals t
                 ON s.route=t.route AND s.origin=t.origin AND s.destination=t.destination
                 AND s.hour=t.hour AND s.day_type=t.day_type
                 WHERE s.matched_days>=3 AND s.sampled_passengers>=10
                   AND t.scheduled_days>=4 AND t.scheduled_crossings>0'''
        for route, origin, dest, kind, hour, passengers, crossings in db.execute(sql):
            training[(route, origin, dest, kind)][hour] = passengers / crossings
    observed = defaultdict(int)
    for row in data['records']:
        if not start <= row['date'] <= end:
            raise ValueError('record outside declared validation dates')
        observed[(row['route'], row['from_stop_id'], row['to_stop_id'], row['date'], row['hour'], row['day_type'])] += row['passengers']
    totals = defaultdict(lambda: [0, 0])
    for (route, origin, dest, day, hour, kind), buses in scheduled_crossings(gtfs, start, end).items():
        group = (route, origin, dest, kind)
        if hour not in training.get(group, {}):
            continue
        cell = totals[(group, hour)]
        cell[0] += observed.get((route, origin, dest, day, hour, kind), 0)
        cell[1] += buses
    by_kind = defaultdict(Counter)
    for group, hours in training.items():
        if len(hours) < 3 or len(set(hours.values())) < 2:
            continue
        kind = group[3]
        row = by_kind[kind]
        row['training_supported_groups'] += 1
        eligible = {h: totals[(group, h)][0] / totals[(group, h)][1]
                    for h in hours if (group, h) in totals and totals[(group, h)][1]}
        row['evaluated_hours'] += len(eligible)
        row['zero_sample_hours'] += sum(value == 0 for value in eligible.values())
        if len(eligible) >= 2:
            row['evaluated_groups'] += 1
            row.update(compare_group(hours, eligible))
    result = {}
    for kind, counts in by_kind.items():
        decisive = counts['concordant'] + counts['discordant']
        result[kind] = {**counts, 'decisive_pairs': decisive,
                        'concordance_on_decisive_pairs': counts['concordant'] / decisive if decisive else None}
    return {'start': start, 'end': end, 'groups_by_day_type': result,
            'limitations': 'One group is a route and directed segment; segment pairs are correlated. Evaluation uses scheduled crossings, sample zeros assume complete ingestion, and the same matching process as training. Timing and service mismatches can bias results. No Sunday is evaluated. Not occupancy accuracy or calibrated label accuracy.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('database', 'validation', 'gtfs', 'output'):
        parser.add_argument('--' + arg, required=True)
    args = parser.parse_args()
    result = evaluate(args.database, args.validation, args.gtfs)
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
