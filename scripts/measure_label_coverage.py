"""Measure provisional label support on tuning sample segment records."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import sqlite3


def measure(database, validation):
    with open(validation, encoding='utf-8') as f:
        data=json.load(f)
    if data['training_start'] < '2026-10-22' or data['training_end'] > '2026-10-24' or data['training_start'] > data['training_end']:
        raise ValueError('Only October 22–24 tuning data is permitted')
    with sqlite3.connect('file:'+str(Path(database).resolve())+'?mode=ro',uri=True) as db:
        meta={k:json.loads(v) for k,v in db.execute('SELECT key,value FROM metadata')}
        if meta['training_end'] >= data['training_start']: raise ValueError('Training must precede tuning')
        sql='''SELECT s.route,s.origin,s.destination,s.day_type,s.hour,1.0*s.sampled_passengers/t.scheduled_crossings FROM service_signals s JOIN scheduled_totals t USING(route,origin,destination,hour,day_type) WHERE s.matched_days>=3 AND s.sampled_passengers>=10 AND t.scheduled_days>=4 AND t.scheduled_crossings>0'''
        groups=defaultdict(dict)
        for route,origin,dest,kind,hour,value in db.execute(sql):groups[(route,origin,dest,kind)][hour]=value
    supported={(*group,hour) for group, hours in groups.items() if len(hours)>=3 and len(set(hours.values()))>=2 for hour in hours}
    total_cells=labelled_cells=total_weight=labelled_weight=0
    for r in data['records']:
        if not data['training_start']<=r['date']<=data['training_end']: raise ValueError('Record outside declared period')
        key=(r['route'],r['from_stop_id'],r['to_stop_id'],r['day_type'],r['hour'])
        total_cells+=1;total_weight+=r['passengers']
        if key in supported: labelled_cells+=1;labelled_weight+=r['passengers']
    return {'tuning_segment_day_hour_records':total_cells,'labelled_records':labelled_cells,'record_coverage':labelled_cells/total_cells if total_cells else None,'sample_passenger_segments':total_weight,'labelled_sample_passenger_segments':labelled_weight,'sample_passenger_segment_coverage':labelled_weight/total_weight if total_weight else None,'limitation':'Matched ticket sample only; not unique riders, tickets, full journeys or actual passenger coverage. Records on the same trip or segment are correlated. Labels are provisional.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',required=True);p.add_argument('--validation',required=True);a=p.parse_args();print(json.dumps(measure(a.database,a.validation),indent=2))
