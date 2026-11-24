"""Compare the stretch labels with simpler predictors on the same tuning hours.

Uses exactly the evaluation in validate_v1_labels.py (same supported training
hours, same tuning-period target ranks, October 22-24 only) and scores three
alternatives on the same evaluated segment-hours:

- citywide: every stretch follows the citywide hourly pattern for its day type
- route: every stretch follows its own route's hourly pattern
- always_typical: predicts "typical" everywhere (a constant baseline)

If the stretch-level model does not beat the citywide and route patterns, its
extra detail adds nothing over "Delhi is busy at 9 am". Agreement is with later
ticket-sample ranks, not with people counted on buses.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from service import scheduled_crossings
from validate_v1_labels import bands

PREDICTORS = ('model', 'route', 'citywide', 'always_typical')


def profiles(db):
    """Hourly sample passengers per scheduled crossing, citywide and per route."""
    sql = '''SELECT {key} t.day_type, t.hour, COALESCE(SUM(s.sampled_passengers), 0), SUM(t.scheduled_crossings)
             FROM scheduled_totals t LEFT JOIN service_signals s USING(route, origin, destination, hour, day_type)
             GROUP BY {key} t.day_type, t.hour'''
    city = {(kind, hour): p / c for kind, hour, p, c in db.execute(sql.format(key='')) if c}
    route = {(r, kind, hour): p / c for r, kind, hour, p, c in db.execute(sql.format(key='t.route,')) if c}
    return city, route


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
        # Same support rule as validate_v1_labels.py and the API's relative_band.
        sql = '''SELECT s.route,s.origin,s.destination,s.day_type,s.hour,
                        1.0*s.sampled_passengers/t.scheduled_crossings
                 FROM service_signals s JOIN scheduled_totals t
                 USING(route,origin,destination,hour,day_type)
                 WHERE s.matched_days>=3 AND s.sampled_passengers>=10
                   AND t.scheduled_days >= CASE WHEN s.day_type IN ('saturday','sunday') THEN 3 ELSE 4 END AND t.scheduled_crossings>0'''
        for route, origin, dest, kind, hour, rate in db.execute(sql):
            training[(route, origin, dest, kind)][hour] = rate
        city, route_profile = profiles(db)
    observed = defaultdict(int)
    for row in data['records']:
        if not start <= row['date'] <= end:
            raise ValueError('Record outside declared tuning dates')
        observed[(row['route'], row['from_stop_id'], row['to_stop_id'], row['date'], row['hour'], row['day_type'])] += row['passengers']
    totals = defaultdict(lambda: [0, 0])
    for (route, origin, dest, day, hour, kind), buses in scheduled_crossings(gtfs, start, end).items():
        group = (route, origin, dest, kind)
        if hour in training.get(group, {}):
            cell = totals[(group, hour)]
            cell[0] += observed.get((route, origin, dest, day, hour, kind), 0)
            cell[1] += buses
    out = defaultdict(Counter)
    for group, hours in training.items():
        predicted = bands(hours)
        if not predicted:
            continue
        route, _, _, kind = group
        target = {h: totals[(group, h)][0] / totals[(group, h)][1] for h in hours if (group, h) in totals and totals[(group, h)][1]}
        observed_bands = bands({h: target[h] for h in set(hours) & set(target)})
        if not observed_bands:
            continue
        # Each alternative ranks the same supported hours, using its own hourly pattern.
        alternatives = {'model': predicted,
                        'route': bands({h: route_profile.get((route, kind, h), 0.0) for h in hours}),
                        'citywide': bands({h: city.get((kind, h), 0.0) for h in hours}),
                        'always_typical': {h: 'typical' for h in hours}}
        counts = out[kind]
        counts['evaluated_groups'] += 1
        for h, outcome in observed_bands.items():
            counts['evaluated_hours'] += 1
            for name in PREDICTORS:
                label = alternatives[name].get(h)
                counts[name + '_agree'] += int(label == outcome)
                counts[name + '_opposite'] += int({label, outcome} == {'likely quieter', 'likely busier'})
    result = {}
    for kind, c in sorted(out.items()):
        n = c['evaluated_hours']
        result[kind] = {'evaluated_groups': c['evaluated_groups'], 'evaluated_hours': n,
                        **{name: {'agreement': c[name + '_agree'] / n, 'opposite_end': c[name + '_opposite'] / n} for name in PREDICTORS}}
    return {'start': start, 'end': end, 'training_end': meta['training_end'], 'by_day_type': result,
            'limitation': 'Agreement with tuning-period ticket-sample ranks over the same supported hours, not with observed occupancy. '
                          'A baseline that cannot rank an hour set (all rates equal) counts as disagreement. Hours share passengers and are correlated.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ('database', 'validation', 'gtfs', 'output'):
        parser.add_argument('--' + argument, required=True)
    args = parser.parse_args()
    result = evaluate(args.database, args.validation, args.gtfs)
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
