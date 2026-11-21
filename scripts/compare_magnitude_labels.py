"""Compare relative-magnitude and rank labels on development dates only.

This exploratory check uses matched ticket samples, not occupancy. It does not
establish day-to-day stability and does not select a production threshold.
"""
import argparse
from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_v1_labels import bands
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from service import scheduled_crossings
from model import day_type


def magnitude(rates, threshold=.25):
    """Labels relative to the unweighted mean across the common supported hours."""
    if len(rates) < 3:
        return {}
    mean = sum(rates.values()) / len(rates)
    if mean <= 0:
        return {}
    return {hour: ('likely busier' if value > mean * (1 + threshold) else
                   'likely quieter' if value < mean * (1 - threshold) else 'typical')
            for hour, value in rates.items()}


def evaluate(database, validation, gtfs):
    data = json.loads(Path(validation).read_text(encoding='utf-8'))
    start, end = data['training_start'], data['training_end']
    if start < '2026-10-22' or end > '2026-10-24' or start > end:
        raise ValueError('Only development dates October 22–24 are permitted')
    with sqlite3.connect('file:' + str(Path(database).resolve()) + '?mode=ro', uri=True) as db:
        meta = {k: json.loads(v) for k, v in db.execute('SELECT key,value FROM metadata')}
        if meta.get('day_type_scheme') != 'weekday_saturday_sunday_v1' or meta['training_end'] >= start:
            raise ValueError('Expected a pre-development separate-day model')
        groups = defaultdict(dict)
        for route, a, b, kind, hour, days, pax, sched_days, buses in db.execute('''
          SELECT s.route,s.origin,s.destination,s.day_type,s.hour,s.matched_days,
                 s.sampled_passengers,t.scheduled_days,t.scheduled_crossings
          FROM service_signals s JOIN scheduled_totals t
          USING(route,origin,destination,day_type,hour) WHERE t.scheduled_crossings>0'''):
            if days >= 3 and pax >= 10 and sched_days >= (3 if kind in ('saturday','sunday') else 4):
                groups[(route,a,b,kind)][hour] = pax / buses
    obs = defaultdict(int)
    for row in data['records']:
        if not start <= row['date'] <= end or row['day_type'] != day_type(date.fromisoformat(row['date'])):
            raise ValueError('Record outside development window or wrong day type')
        obs[(row['route'],row['from_stop_id'],row['to_stop_id'],row['date'],row['hour'],row['day_type'])] += row['passengers']
    target = defaultdict(lambda: [0,0])
    for (route,a,b,day,hour,kind), buses in scheduled_crossings(gtfs,start,end).items():
        value=target[(route,a,b,kind,hour)];value[0]+=obs.get((route,a,b,day,hour,kind),0);value[1]+=buses
    report=defaultdict(Counter)
    for group, rates in groups.items():
        available={h: target[(*group,h)][0]/target[(*group,h)][1] for h in rates if target[(*group,h)][1]}
        common={h: rates[h] for h in available}
        if len(common)<3 or len(set(common.values()))<2 or len(set(available.values()))<2:
            continue
        rank_pred, rank_target = bands(common), bands(available)
        mag_pred, mag_target = magnitude(common), magnitude(available)
        if not mag_pred or not mag_target: continue
        c=report[group[3]];c['groups']+=1
        for h in common:
            c['hours']+=1;c['rank_agreement']+=rank_pred[h]==rank_target[h]
            c['magnitude_agreement']+=mag_pred[h]==mag_target[h]
            c['rank_busier']+=rank_pred[h]=='likely busier'
            c['magnitude_busier']+=mag_pred[h]=='likely busier'
    return {'start':start,'end':end,'threshold':.25,'groups':{k:dict(v) for k,v in report.items()},'limitations':'Different target definitions; descriptive agreement not a head-to-head accuracy comparison. Same cells, but rank and magnitude predict different targets. Unweighted mean of supported hours, not all-day or service-weighted. No across-day stability check; no Sunday target. Ticket sample, not occupancy. Correlated observations. No final-week records read.'}

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('database','validation','gtfs','output'):p.add_argument('--'+key,required=True)
    a=p.parse_args();out=Path(a.output)
    if out.exists():raise FileExistsError('Refusing to overwrite existing report')
    result=evaluate(a.database,a.validation,a.gtfs)
    with out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2))
