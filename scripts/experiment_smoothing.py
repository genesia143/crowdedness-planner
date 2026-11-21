"""Development-only fixed-parameter comparison; no model or final-week data is read."""
import argparse
import collections
import datetime
import json
import itertools
import sqlite3

DATES = ('2026-10-22', '2026-10-23', '2026-10-24')

def run(database, validation):
    with open(validation, encoding='utf-8') as f:
        target = json.load(f)
    if (target['training_start'], target['training_end']) != (DATES[0], DATES[-1]):
        raise ValueError('Requires Oct 22–24 development target only')
    observed = collections.defaultdict(int)
    for r in target['records']:
        if r['date'] not in DATES:
            raise ValueError('Target includes dates outside Oct 22–24')
        observed[(r['date'],r['route'],r['from_stop_id'],r['to_stop_id'],r['hour'])] += r['passengers']
    del target
    report = collections.defaultdict(lambda: collections.defaultdict(float))
    with sqlite3.connect('file:' + database + '?mode=ro', uri=True) as db:
        meta = {k: json.loads(v) for k, v in db.execute('SELECT key,value FROM metadata')}
        if meta['training_end'] != '2026-10-21':
            raise ValueError('Model must end October 21')
        rows = db.execute("""SELECT t.route,t.origin,t.destination,t.hour,t.day_type,t.scheduled_days,t.scheduled_crossings,
               COALESCE(s.sampled_passengers,0) FROM scheduled_totals t LEFT JOIN service_signals s
               USING(route,origin,destination,hour,day_type)
               WHERE t.day_type IN ('weekday','saturday') AND t.scheduled_days>0 AND t.scheduled_crossings>0
               ORDER BY t.route""")
        for route, group in itertools.groupby(rows, key=lambda row: row[0]):
            points = {(a,b,h,d): (n,crossings,pax) for _,a,b,h,d,n,crossings,pax in group}
            outgoing, incoming = collections.defaultdict(set), collections.defaultdict(set)
            for a,b,h,d in points:
                outgoing[a].add(b); incoming[b].add(a)
            for (a,b,h,d), (days,crossings,pax) in points.items():
                base = pax / crossings
                nearby = [points[(a,b,x,d)] for x in (h-1,h,h+1) if (a,b,x,d) in points]
                smooth_t = sum(x[2] for x in nearby) / sum(x[1] for x in nearby)
                shrink = pax/(pax+10)*base + 10/(pax+10)*smooth_t
                neighbours = []
                if len(incoming[a])==1 and len(outgoing[a])==1:
                    key=(next(iter(incoming[a])),a,h,d)
                    if key in points: neighbours.append(points[key][2]/points[key][1])
                if len(outgoing[b])==1 and len(incoming[b])==1:
                    key=(b,next(iter(outgoing[b])),h,d)
                    if key in points: neighbours.append(points[key][2]/points[key][1])
                if not neighbours: continue
                spatial = 0.75*base + 0.25*sum(neighbours)/len(neighbours)
                for date in DATES:
                    if ('saturday' if datetime.date.fromisoformat(date).weekday()==5 else 'weekday') != d: continue
                    outcome=observed.get((date,route,a,b,h),0) / (crossings/days)
                    acc=report[d]; acc['cells']+=1; acc['target_zero_cells']+=outcome==0
                    for name,pred in [('baseline',base),('temporal_shrink',shrink),('spatial_smooth',spatial)]:
                        acc[name+'_absolute_error']+=abs(pred-outcome)
    for acc in report.values():
        for key in ('baseline','temporal_shrink','spatial_smooth'):
            acc[key+'_mae']=acc.pop(key+'_absolute_error')/acc['cells'] if acc['cells'] else None
    return {'parameters': {'spatial_weight':0.25,'temporal_pseudopassengers':10,'window_hours':3},'days':list(DATES),'results':dict(report), 'caveats':'Same cells across candidates, only cells with unique adjacent segment. All scheduled hours included, including observed zero days; zero assumes complete sample capture. Target per scheduled crossing approximates daily schedule from training. This is not true crowding, schedule assumes same service daily, segments and days are correlated, training and target sampling can share systematic biases; the two weekdays and one Saturday cannot assess Sunday. MAE averages segment-hours, not passengers or journeys. Parameters fixed beforehand but not independently validated.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--database',required=True); p.add_argument('--validation',required=True); p.add_argument('--output',required=True)
    a=p.parse_args(); result=run(a.database,a.validation)
    with open(a.output,'x',encoding='utf-8') as f: json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))
