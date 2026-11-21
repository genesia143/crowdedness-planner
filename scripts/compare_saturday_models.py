"""Compare pooled-weekend and Saturday-specific labels on identical tuning cells."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sqlite3
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from service import scheduled_crossings
from validate_v1_labels import bands


def compare(pooled, split, validation, gtfs):
    data=json.loads(Path(validation).read_text())
    if data['training_start']<'2026-10-22' or data['training_end']>'2026-10-24':raise ValueError('Only tuning dates allowed')
    def training(path,kind,min_days):
        with sqlite3.connect('file:'+str(Path(path).resolve())+'?mode=ro',uri=True) as db:
            meta={k:json.loads(v) for k,v in db.execute('SELECT key,value FROM metadata')}
            if meta['training_end']>=data['training_start']:raise ValueError('Training overlaps tuning')
            groups=defaultdict(dict)
            query='''SELECT s.route,s.origin,s.destination,s.hour,1.0*s.sampled_passengers/t.scheduled_crossings FROM service_signals s JOIN scheduled_totals t USING(route,origin,destination,day_type,hour) WHERE s.day_type=? AND s.matched_days>=3 AND s.sampled_passengers>=10 AND t.scheduled_days>=? AND t.scheduled_crossings>0'''
            for r,a,b,h,v in db.execute(query,(kind,min_days)):groups[(r,a,b)][h]=v
        return groups
    pooled_groups=training(pooled,'weekend',4); split_groups=training(split,'saturday',3)
    samples=defaultdict(int)
    for r in data['records']:
        if not data['training_start']<=r['date']<=data['training_end']:raise ValueError('Record outside tuning range')
        if r['day_type']=='saturday':samples[(r['route'],r['from_stop_id'],r['to_stop_id'],r['date'],r['hour'])]+=r['passengers']
    totals=defaultdict(lambda:[0,0])
    for (r,a,b,d,h,kind),buses in scheduled_crossings(gtfs,data['training_start'],data['training_end']).items():
        if kind=='saturday':
            v=totals[(r,a,b,h)];v[0]+=samples[(r,a,b,d,h)];v[1]+=buses
    counts=Counter()
    for group in pooled_groups.keys() & split_groups.keys():
        p=pooled_groups[group];s=split_groups[group];pb,sb=bands(p),bands(s)
        if not pb or not sb:continue
        common=set(pb)&set(sb)
        target=bands({h:totals[(*group,h)][0]/totals[(*group,h)][1] for h in common if totals[(*group,h)][1]})
        if not target:continue
        counts['groups']+=1
        for h,label in target.items():
            counts['hours']+=1;counts['pooled_agree']+=pb[h]==label;counts['split_agree']+=sb[h]==label
            counts['both_agree']+=pb[h]==label and sb[h]==label
            counts['both_wrong']+=pb[h]!=label and sb[h]!=label
    n=counts['hours']
    return {**counts,'pooled_agreement':counts['pooled_agree']/n if n else None,'split_agreement':counts['split_agree']/n if n else None,'limitations':'Same supported segment-hours only; target is one Saturday of matched ticket samples, not occupancy. Hours and routes are correlated; different model reference hours and support rules affect labels. Sunday not tested.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('pooled','split','validation','gtfs','output'):p.add_argument('--'+name,required=True)
    a=p.parse_args();result=compare(a.pooled,a.split,a.validation,a.gtfs)
    with Path(a.output).open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))
