"""Evaluate the frozen V1 ticket signal against October 22–24 only.

This evaluates the ticket sample, not actual passenger occupancy. The final
week is deliberately rejected even when a caller supplies it by mistake.
"""
import argparse
from datetime import date
from collections import defaultdict
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from service import scheduled_crossings
from model import day_type


def evaluate(database, validation, gtfs):
    with open(validation, encoding='utf-8') as handle:
        data = json.load(handle)
    start, end = data['training_start'], data['training_end']
    if start < '2026-10-22' or end > '2026-10-24' or end < start:
        raise ValueError('development evaluation is restricted to October 22–24, 2026')
    with sqlite3.connect('file:' + str(Path(database).resolve()) + '?mode=ro', uri=True) as db:
        meta = {key: json.loads(value) for key, value in db.execute('SELECT key,value FROM metadata')}
        if meta.get('day_type_scheme') != 'weekday_saturday_sunday_v1':
            raise ValueError('Use a model rebuilt with separate Saturday and Sunday categories')
        if meta['training_end'] >= start:
            raise ValueError('training must end before the evaluation period')
        prediction = {}
        sql = '''SELECT t.route,t.origin,t.destination,t.hour,t.day_type,
                        COALESCE(s.sampled_passengers,0),t.scheduled_crossings
                 FROM scheduled_totals t LEFT JOIN service_signals s
                 ON t.route=s.route AND t.origin=s.origin AND t.destination=s.destination
                 AND t.hour=s.hour AND t.day_type=s.day_type
                 WHERE t.scheduled_crossings > 0'''
        for route, origin, dest, hour, kind, passengers, buses in db.execute(sql):
            prediction[(route, origin, dest, hour, kind)] = passengers / buses
    observations = defaultdict(int)
    for row in data['records']:
        if not start <= row['date'] <= end:
            raise ValueError('record outside declared validation dates')
        if row['day_type'] != day_type(date.fromisoformat(row['date'])): raise ValueError('Tuning day type does not match calendar date')
        key = (row['route'], row['from_stop_id'], row['to_stop_id'], row['date'], row['hour'], row['day_type'])
        observations[key] += row['passengers']
    schedule = scheduled_crossings(gtfs, start, end)
    stats = defaultdict(lambda: {'scheduled_cells': 0, 'matched_cells': 0, 'prediction_cells': 0,
                                 'absolute_error_sum': 0.0, 'observed_total': 0, 'scheduled_crossings': 0})
    for (route, origin, dest, day, hour, kind), buses in schedule.items():
        cell = (route, origin, dest, day, hour, kind)
        sample = observations.get(cell, 0)
        row = stats[kind]
        row['scheduled_cells'] += 1
        row['matched_cells'] += bool(sample)
        row['observed_total'] += sample
        row['scheduled_crossings'] += buses
        expected = prediction.get((route, origin, dest, hour, kind))
        if expected is not None:
            row['prediction_cells'] += 1
            row['absolute_error_sum'] += abs(expected - sample / buses)
    results = {}
    for kind, row in stats.items():
        n = row.pop('prediction_cells')
        total = row.pop('absolute_error_sum')
        results[kind] = {**row, 'prediction_cells': n,
                         'prediction_coverage': n / row['scheduled_cells'] if row['scheduled_cells'] else None,
                         'mean_absolute_error_per_crossing': total / n if n else None}
    return {'validation_start': start, 'validation_end': end, 'training_start': meta['training_start'],
            'training_end': meta['training_end'], 'matching_quality': data['quality'],
            'unmatched_to_schedule_records': sum(1 for key in observations if key not in schedule),
            'day_types': results,
            'limitations': 'Ticket creation hour is treated as the crossing hour; zero sample records assume complete ingestion. Schedule-only training cells are evaluated as zero-sample baselines even where the user API reports insufficient evidence. The target uses the same matching process and is not independent occupancy. Day types follow the indexed model; no Sunday occurs in this tuning interval.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ('database', 'validation', 'gtfs', 'output'):
        parser.add_argument('--' + argument, required=True)
    args = parser.parse_args()
    report = evaluate(args.database, args.validation, args.gtfs)
    Path(args.output).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
