"""Compare provisional hour labels with matched ticket rates in tuning only.

The target labels are relative ranks within the *same supported hours* as the
training labels. They are a noisy ticket-sample reference, not occupancy truth.
"""
import argparse
from datetime import date
from collections import Counter, defaultdict
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from service import scheduled_crossings
from model import day_type


def bands(rates):
    if len(rates) < 3 or len(set(rates.values())) < 2:
        return {}
    result = {}
    for hour, value in rates.items():
        rank = (sum(v < value for v in rates.values()) +
                0.5 * sum(v == value for v in rates.values())) / len(rates)
        result[hour] = 'likely quieter' if rank < 1 / 3 else 'likely busier' if rank > 2 / 3 else 'typical'
    return result


def compare(training, target):
    """Compare actual training labels to target labels on available hours."""
    common = set(training) & set(target)
    predicted = bands(training)
    observed = bands({h: target[h] for h in common})
    if not predicted or not observed:
        return Counter(), len(common)
    return Counter((predicted[h], observed[h]) for h in common), 0


def evaluate(database, validation, gtfs):
    with open(validation, encoding='utf-8') as f:
        data = json.load(f)
    start, end = data['training_start'], data['training_end']
    if start < '2026-10-22' or end > '2026-10-24' or end < start:
        raise ValueError('Only October 22–24 tuning data is permitted')
    training = defaultdict(dict)
    with sqlite3.connect('file:' + str(Path(database).resolve()) + '?mode=ro', uri=True) as db:
        meta = {k: json.loads(v) for k, v in db.execute('SELECT key,value FROM metadata')}
        if meta.get('day_type_scheme') != 'weekday_saturday_sunday_v1':
            raise ValueError('Use a model rebuilt with separate Saturday and Sunday categories')
        if meta['training_end'] >= start:
            raise ValueError('Training must precede tuning')
        sql = '''SELECT s.route,s.origin,s.destination,s.day_type,s.hour,
                        1.0*s.sampled_passengers/t.scheduled_crossings
                 FROM service_signals s JOIN scheduled_totals t
                 USING(route,origin,destination,hour,day_type)
                 WHERE s.matched_days>=3 AND s.sampled_passengers>=10
                   AND t.scheduled_days >= CASE WHEN s.day_type IN ('saturday','sunday') THEN 3 ELSE 4 END AND t.scheduled_crossings>0'''
        for route, origin, dest, kind, hour, rate in db.execute(sql):
            training[(route, origin, dest, kind)][hour] = rate
    observed = defaultdict(int)
    for row in data['records']:
        if not start <= row['date'] <= end:
            raise ValueError('Record outside declared tuning dates')
        key = (row['route'], row['from_stop_id'], row['to_stop_id'], row['date'], row['hour'], row['day_type'])
        observed[key] += row['passengers']
    totals = defaultdict(lambda: [0, 0])
    for (route, origin, dest, day, hour, kind), buses in scheduled_crossings(gtfs, start, end).items():
        group = (route, origin, dest, kind)
        if hour in training.get(group, {}):
            cell = totals[(group, hour)]
            cell[0] += observed.get((route, origin, dest, day, hour, kind), 0)
            cell[1] += buses
    out = defaultdict(Counter)
    for group, hours in training.items():
        if not bands(hours):
            continue
        target = {h: totals[(group, h)][0] / totals[(group, h)][1]
                  for h in hours if (group, h) in totals and totals[(group, h)][1]}
        matrix, excluded = compare(hours, target)
        counts = out[group[3]]
        counts['training_supported_groups'] += 1
        counts['training_supported_hours'] += len(hours)
        counts['common_hours_excluded_no_target_rank'] += excluded
        if matrix:
            counts['evaluated_groups'] += 1
            for (prediction, outcome), count in matrix.items():
                counts['prediction=' + prediction + '|target=' + outcome] += count
                counts['evaluated_hours'] += count
                counts['agreement'] += count if prediction == outcome else 0
    result = {}
    for kind, counts in out.items():
        result[kind] = {**counts, 'agreement_rate': counts['agreement'] / counts['evaluated_hours'] if counts['evaluated_hours'] else None}
    return {'start': start, 'end': end, 'by_day_type': result,
            'limitation': 'Predictions use all supported training hours as the API does; target ranks use those with tuning service, not measured occupancy. Zero sample assumes complete ingestion; same matching and schedule are used in both periods. Ties receive midranks. Groups and hours are correlated. Weekend tuning contains Saturday only.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ('database', 'validation', 'gtfs', 'output'):
        parser.add_argument('--' + argument, required=True)
    args = parser.parse_args()
    result = evaluate(args.database, args.validation, args.gtfs)
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
