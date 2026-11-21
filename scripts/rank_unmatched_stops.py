"""Rank unresolved route/stop/role combinations by affected unmatched tickets."""
import argparse
import csv
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from model import StopMatcher, normalize, route_patterns
from reviewed_mappings import inspect


def rank(pairs,gtfs,review,output,limit=100):
    names,patterns=route_patterns(gtfs)
    audit=inspect(review,gtfs,confirmed=True)
    reviewed={(normalize(r['route']),normalize(r['ticket_stop_name']),r['used_as']):r['stop_id'] for r in audit if r['status']=='accepted'}
    matcher=StopMatcher(names,patterns,reviewed=reviewed)
    counts=Counter()
    with open(pairs,encoding='utf-8-sig',newline='') as handle:
        for row in csv.DictReader(handle):
            route=normalize(row['route'])
            if route not in patterns: continue
            for role,field in [('boarding','boarding_name'),('destination','destination_name')]:
                name=row[field]
                if (route,normalize(name),role) in reviewed or matcher.resolve(route,name)[0] is not None: continue
                counts[(row['route'],name,role)]+=int(row['ticket_rows'])
    with open(output,'w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.writer(handle); writer.writerow(['route','ticket_stop','role','affected_unmatched_ticket_rows','candidate_stop_id','candidate_gtfs_name','similarity_percent','decision','notes'])
        for (route,name,role),count in counts.most_common(limit):
            route_key=normalize(route)
            ids={stop for path in patterns[route_key] for stop in path}
            ranked=sorted(((SequenceMatcher(None,normalize(name),normalize(names[stop])).ratio(),stop) for stop in ids),reverse=True)
            if ranked:
                score,stop=ranked[0]; writer.writerow([route,name,role,count,stop,names[stop],round(score*100,1),'',''])
            else: writer.writerow([route,name,role,count,'','','','',''])
    print('Wrote',min(limit,len(counts)),'of',len(counts),'unresolved route/stop/role combinations.')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('pairs','gtfs','review','output'):p.add_argument('--'+name,required=True)
    p.add_argument('--limit',type=int,default=100); a=p.parse_args()
    if a.limit<=0:p.error('limit must be positive')
    rank(a.pairs,a.gtfs,a.review,a.output,a.limit)
