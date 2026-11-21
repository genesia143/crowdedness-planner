"""Compare split-day support thresholds on Oct 22-24 development data.

Statistics are matched-ticket proxies, not occupancy; variants are exploratory.
"""
import argparse
from datetime import date
from collections import Counter, defaultdict
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_v1_ranking import compare_group
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from service import scheduled_crossings
from model import day_type


def evaluate(database, validation, gtfs, variants):
    data = json.loads(Path(validation).read_text(encoding='utf-8'))
    start, end = data['training_start'], data['training_end']
    if start < '2026-10-22' or end > '2026-10-24' or start > end:
        raise ValueError('evaluation restricted to October 22–24, 2026')
    with sqlite3.connect('file:' + str(Path(database).resolve()) + '?mode=ro', uri=True) as db:
        meta = {k: json.loads(v) for k, v in db.execute('SELECT key,value FROM metadata')}
        if meta.get('day_type_scheme') != 'weekday_saturday_sunday_v1':
            raise ValueError('Use a model rebuilt with separate Saturday and Sunday categories')
        if meta['training_end'] >= start:
            raise ValueError('training must end before tuning')
        rows = list(db.execute('''SELECT s.route,s.origin,s.destination,s.day_type,s.hour,
            s.matched_days,s.sampled_passengers,t.scheduled_days,t.scheduled_crossings
            FROM service_signals s JOIN scheduled_totals t
            USING(route,origin,destination,hour,day_type) WHERE t.scheduled_crossings>0'''))
    observed = defaultdict(int)
    for row in data['records']:
        if not start <= row['date'] <= end:
            raise ValueError('record outside declared tuning period')
        if row['day_type'] != day_type(date.fromisoformat(row['date'])): raise ValueError('Tuning day type does not match calendar date')
        observed[(row['route'],row['from_stop_id'],row['to_stop_id'],row['date'],row['hour'],row['day_type'])] += row['passengers']
    targets = defaultdict(lambda: [0,0])
    for (route,origin,dest,day,hour,kind), buses in scheduled_crossings(gtfs,start,end).items():
        cell = targets[(route,origin,dest,kind,hour)]
        cell[0] += observed.get((route,origin,dest,day,hour,kind),0)
        cell[1] += buses
    reports = []
    for days, passengers, scheduled_days in variants:
        groups = defaultdict(dict)
        for route,origin,dest,kind,hour,matched,n,sd,crossings in rows:
            if matched >= days and n >= passengers and sd >= (3 if kind in ('saturday','sunday') else scheduled_days):
                groups[(route,origin,dest,kind)][hour] = n/crossings
        groups = {g: hours for g,hours in groups.items() if len(hours)>=3 and len(set(hours.values()))>=2}
        supported = {(*g,h) for g,hours in groups.items() for h in hours}
        total = sum(observed.values())
        covered = sum(n for (route,origin,dest,day,hour,kind),n in observed.items() if (route,origin,dest,kind,hour) in supported)
        counts = defaultdict(Counter)
        from validate_v1_labels import compare
        label_counts = defaultdict(Counter)
        for group,hours in groups.items():
            eligible = {h:targets[(*group,h)][0]/targets[(*group,h)][1] for h in hours if targets[(*group,h)][1]}
            counts[group[3]].update(compare_group(hours,eligible))
            matrix, excluded = compare(hours, eligible)
            label_counts[group[3]]['evaluated_hours'] += sum(matrix.values())
            label_counts[group[3]]['agreement'] += sum(n for (a,b),n in matrix.items() if a == b)
        by_kind = {}
        for kind,c in counts.items():
            decisive = c['concordant']+c['discordant']
            by_kind[kind] = {**c, 'decisive_pairs':decisive, 'concordance':c['concordant']/decisive if decisive else None}
        reports.append({'minimum_matched_days':days,'minimum_sample_passengers':passengers,'minimum_scheduled_weekdays':scheduled_days,'minimum_scheduled_weekend_days':3,
                        'sample_passenger_segments':total,'covered_sample_passenger_segments':covered,
                        'sample_passenger_segment_coverage':covered/total if total else None,'rankings':by_kind,
                        'labels':{k: {**v, 'agreement_rate':v['agreement']/v['evaluated_hours'] if v['evaluated_hours'] else None} for k,v in label_counts.items()}})
    return {'start':start,'end':end,'variants':reports,'limitations':'Exploratory tuning, not independent validation. Match-derived sample, not occupancy. Coverage counts passenger-segments, not riders or journeys. Pairwise comparisons are correlated, exclude ties from concordance and cannot be treated as independent. No Sunday occurs in the tuning window; day types depend on the supplied model.'}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('database','validation','gtfs','output'): p.add_argument('--'+key,required=True)
    a=p.parse_args()
    result=evaluate(a.database,a.validation,a.gtfs,[(3,10,4),(2,5,4),(4,20,4)])
    Path(a.output).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
