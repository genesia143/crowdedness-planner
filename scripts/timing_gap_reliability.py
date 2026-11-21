"""Compare tuning label agreement by training-derived route timing gaps.

Only development dates are accepted. Thresholds filter a fixed set of evaluated
segment-hours; they do not recompute ranks or establish occupancy accuracy.
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


def summarize(rows, thresholds=(0.05, 0.10, 0.25, 1.0)):
    """Rows are (day_type, training_gap, prediction, observed), same population."""
    out = {}
    for kind in sorted({row[0] for row in rows}):
        population = [r for r in rows if r[0] == kind]
        results = []
        for threshold in thresholds:
            selected = [r for r in population if r[1] <= threshold]
            opposite = sum({p, o} == {'likely quieter', 'likely busier'} for _, _, p, o in selected)
            correct = sum(p == o for _, _, p, o in selected)
            results.append({'max_training_route_gap': threshold, 'hours': len(selected),
                            'fraction_of_common_population': len(selected)/len(population) if population else None,
                            'agreement': correct/len(selected) if selected else None,
                            'opposite_ends': opposite/len(selected) if selected else None})
        out[kind] = {'common_hours': len(population), 'thresholds': results}
    return out


def evaluate(database, validation, gtfs):
    data = json.loads(Path(validation).read_text())
    start, end = data['training_start'], data['training_end']
    if start < '2026-10-22' or end > '2026-10-24' or end < start:
        raise ValueError('Only October 22–24 tuning data is permitted')
    training = defaultdict(dict)
    with sqlite3.connect('file:' + str(Path(database).resolve()) + '?mode=ro', uri=True) as db:
        meta = {k: json.loads(v) for k,v in db.execute('SELECT key,value FROM metadata')}
        if meta['training_end'] >= start:
            raise ValueError('Training must precede tuning')
        # The all-signal total includes ticket samples without scheduled crossings.
        all_counts = dict(db.execute('SELECT route, SUM(total) FROM signals GROUP BY route'))
        scheduled_counts = dict(db.execute('SELECT route, SUM(sampled_passengers) FROM service_signals GROUP BY route'))
        gaps = {r: max(0, (n - scheduled_counts.get(r, 0)) / n) for r, n in all_counts.items() if n}
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
        observed[(row['route'],row['from_stop_id'],row['to_stop_id'],row['date'],row['hour'],row['day_type'])] += row['passengers']
    totals = defaultdict(lambda: [0, 0])
    legacy_weekend = any(group[3] == 'weekend' for group in training)
    for (route, origin, dest, day, hour, kind), buses in scheduled_crossings(gtfs,start,end).items():
        if legacy_weekend and kind in ('saturday', 'sunday'):
            kind = 'weekend'
        group = (route,origin,dest,kind)
        if hour in training.get(group, {}):
            totals[(group,hour)][0] += observed.get((route,origin,dest,day,hour,kind),0)
            totals[(group,hour)][1] += buses
    rows = []
    for group, hours in training.items():
        predicted = bands(hours)
        target = {h: totals[(group,h)][0]/totals[(group,h)][1] for h in hours
                  if (group,h) in totals and totals[(group,h)][1]}
        observed_bands = bands(target)
        if predicted and observed_bands and group[0] in gaps:
            for h in set(predicted) & set(observed_bands):
                rows.append((group[3],gaps[group[0]],predicted[h],observed_bands[h]))
    return {'dates': [start,end], 'by_day_type': summarize(rows),
            'scope': 'Labels are fixed before thresholds. Fractions use common evaluated segment-hours, not all journeys. Route gap estimated from matched training samples; tuning targets and ranks share timetable and matching assumptions. No actual occupancy truth. Associations are not causal.'}

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('database','validation','gtfs','output'):
        p.add_argument('--'+name, required=True)
    a=p.parse_args()
    result=evaluate(a.database,a.validation,a.gtfs)
    with Path(a.output).open('x') as f:
        json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))
