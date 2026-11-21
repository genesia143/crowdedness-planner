"""Evaluate holiday exclusion and daily stability using October 1–24 development data.

Uses the original supported weekday cells and the existing ticket-sample target;
no passenger occupancy claims. Run with sufficient memory for training JSON.
"""
import argparse
from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from model import day_type
from service import scheduled_crossings
sys.path.insert(0, str(Path(__file__).resolve().parent))
from compare_magnitude_labels import magnitude

HOLIDAYS = {'2026-10-02', '2026-10-20'}
TRAIN_START, TRAIN_END = '2026-10-01', '2026-10-21'
TARGET_START, TARGET_END = '2026-10-22', '2026-10-23'


def check_records(data, start, end):
    if (data['training_start'], data['training_end']) != (start, end):
        raise ValueError('Unexpected input dates; only development periods are allowed')
    for row in data['records']:
        if not start <= row['date'] <= end or row['day_type'] != day_type(date.fromisoformat(row['date'])):
            raise ValueError('Record date outside declared development range or incorrect day type')


def remove_holidays(passengers, crossings, holiday_passengers, holiday_crossings):
    """Subtract both sides of the rate for exactly the excluded dates."""
    if crossings <= holiday_crossings or passengers < holiday_passengers:
        return None
    return (passengers-holiday_passengers)/(crossings-holiday_crossings)


def run(database, training, target, gtfs):
    groups = defaultdict(dict)
    with sqlite3.connect('file:' + str(Path(database).resolve()) + '?mode=ro', uri=True) as db:
        meta = {k: json.loads(v) for k, v in db.execute('SELECT key,value FROM metadata')}
        if (meta.get('training_start'), meta.get('training_end')) != (TRAIN_START, TRAIN_END):
            raise ValueError('Only October 1–21 training model permitted')
        for route, a, b, hour, pax, buses in db.execute('''
          SELECT s.route,s.origin,s.destination,s.hour,s.sampled_passengers,t.scheduled_crossings
          FROM service_signals s JOIN scheduled_totals t USING(route,origin,destination,day_type,hour)
          WHERE s.day_type='weekday' AND s.matched_days>=3 AND s.sampled_passengers>=10
          AND t.scheduled_days>=4 AND t.scheduled_crossings>0'''):
            groups[(route,a,b)][hour] = (pax,buses)
    # Derive denominators for each holiday and tuning day from their actual GTFS service calendar.
    service = {}
    for day in sorted(HOLIDAYS | {TARGET_START, TARGET_END}):
        filtered = {}
        for (route,a,b,day_key,hour,kind), buses in scheduled_crossings(gtfs,day,day).items():
            if kind == 'weekday' and hour in groups.get((route,a,b), {}):
                filtered[(route,a,b,hour)] = buses
        service[day] = filtered
    training_data = json.loads(Path(training).read_text())
    check_records(training_data, TRAIN_START, TRAIN_END)
    daily = defaultdict(Counter)
    for row in training_data['records']:
        key=(row['route'],row['from_stop_id'],row['to_stop_id'])
        if row['day_type']=='weekday' and row['hour'] in groups.get(key,{}):
            daily[(key,row['date'])][row['hour']] += row['passengers']
    del training_data
    target_data=json.loads(Path(target).read_text())
    check_records(target_data,'2026-10-22','2026-10-24')
    target_pax=Counter()
    for row in target_data['records']:
        if TARGET_START <= row['date'] <= TARGET_END:
            target_pax[(row['route'],row['from_stop_id'],row['to_stop_id'],row['hour'])] += row['passengers']
    del target_data
    result=Counter()
    for group, hours in groups.items():
        original={h:p/b for h,(p,b) in hours.items()}
        adjusted={}
        for h,(p,b) in hours.items():
            key=(*group,h)
            hp=sum(daily.get((group,d),{}).get(h,0) for d in HOLIDAYS)
            hb=sum(service[d].get(key,0) for d in HOLIDAYS)
            rate=remove_holidays(p,b,hp,hb)
            if rate is not None:
                adjusted[h]=rate
        observed={}
        for h in original.keys() & adjusted.keys():
            key=(*group,h)
            b=sum(service[d].get(key,0) for d in (TARGET_START,TARGET_END))
            if b: observed[h]=target_pax[key]/b
        common=observed.keys()
        baseline=magnitude({h:original[h] for h in common})
        candidate=magnitude({h:adjusted[h] for h in common})
        truth=magnitude(observed)
        if not truth or not candidate or not baseline:
            continue
        result['groups'] += 1
        # Daily variation is assessed only on ticket-positive daily cells; no zero
        # or GTFS service assumptions enter this exploratory stability statistic.
        for h in common:
            result['hours'] += 1
            result['original_agrees'] += baseline[h] == truth[h]
            result['excluded_agrees'] += candidate[h] == truth[h]
            result['label_changed'] += baseline[h] != candidate[h]
            if candidate[h] != 'likely busier':
                continue
            ratios=[]
            for daynum in range(1,22):
                day=f'2026-10-{daynum:02d}'
                if day in HOLIDAYS or date.fromisoformat(day).weekday()>=5: continue
                vals=daily.get((group,day),{})
                # Positive-only daily comparison, restricted to the same supported hours.
                positive=[vals[k] / hours[k][1] for k in common if vals.get(k,0)>0]
                if len(positive)>=3 and vals.get(h,0)>0:
                    ratios.append((vals[h]/hours[h][1])/(sum(positive)/len(positive)))
            if len(ratios)>=3:
                result['busier_with_3_positive_days']+=1
                result['busier_majority_above_1_25']+=sum(v>1.25 for v in ratios)>len(ratios)/2
    return {'counts':dict(result), 'limitations':'October 1–21 training, October 22–23 weekday target, matched ticket-sample rates and static GTFS; no occupancy ground truth. The identical original support is retained after exclusion; the sample therefore favours comparability rather than evaluating support changes. Daily positive-only stability excludes zero-ticket days and normalizes by aggregate scheduled service, so selection bias and varying daily service prevent interpretation as probability or formal day-level confirmation. Cells and routes are correlated.'}

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('database','training','target','gtfs','output'): p.add_argument('--'+k,required=True)
    a=p.parse_args(); out=Path(a.output)
    if out.exists(): raise FileExistsError(out)
    result=run(a.database,a.training,a.target,a.gtfs)
    with out.open('x') as f: json.dump(result,f,indent=2); f.write('\n')
    print(json.dumps(result,indent=2))
