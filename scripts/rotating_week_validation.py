"""Compare weekday signal ordering over three rotating October development weeks.

The three folds overlap in training data and are not independent trials. This
script reads only an already-built October 1–21 training artifact, not the raw
CSV or final-week records. It compares the ticket sample, not physical crowding.
"""
import argparse
from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_v1_ranking import compare_group
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from model import day_type
from service import scheduled_crossings

WEEKS=(('2026-10-01','2026-10-07'),('2026-10-08','2026-10-14'),('2026-10-15','2026-10-21'))


def evaluate(records_path, gtfs):
    data=json.loads(Path(records_path).read_text(encoding='utf-8'))
    if (data['training_start'],data['training_end']) != ('2026-10-01','2026-10-21'):
        raise ValueError('Requires development records from October 1–21 only')
    observations=defaultdict(int)
    for row in data['records']:
        day=row['date']
        if not WEEKS[0][0] <= day <= WEEKS[-1][1] or row['day_type'] != day_type(date.fromisoformat(day)):
            raise ValueError('Record outside development dates or inconsistent day type')
        if row['day_type']=='weekday':
            observations[(row['route'],row['from_stop_id'],row['to_stop_id'],day,row['hour'])] += row['passengers']
    del data
    # Each cell is represented by per-week sample counts, number of observed
    # days, scheduled crossings and scheduled days. Unmatched schedule cells
    # are retained as zero sample observations.
    cells=defaultdict(lambda: [[0,0,0,0] for _ in WEEKS])
    excluded=Counter()
    schedule=scheduled_crossings(gtfs,WEEKS[0][0],WEEKS[-1][1])
    for (route,a,b,day,hour,kind),buses in schedule.items():
        if kind!='weekday':continue
        week=next(i for i,(start,end) in enumerate(WEEKS) if start<=day<=end)
        n=observations.get((route,a,b,day,hour),0)
        cell=cells[(route,a,b,hour)][week]
        cell[0]+=n;cell[1]+=int(n>0);cell[2]+=buses;cell[3]+=1
    for key,n in observations.items():
        route,a,b,day,hour=key
        if (route,a,b,day,hour,'weekday') not in schedule:excluded['unscheduled_sample_passenger_segments']+=n
    folds=[]
    for held,(start,end) in enumerate(WEEKS):
        groups=defaultdict(lambda: ({},{})); counts=Counter()
        for (route,a,b,hour),weeks in cells.items():
            hold=weeks[held];other=[w for i,w in enumerate(weeks) if i!=held]
            pax=sum(w[0] for w in other); observed_days=sum(w[1] for w in other)
            crossings=sum(w[2] for w in other);scheduled_days=sum(w[3] for w in other)
            counts['target_sample_passenger_segments']+=hold[0]
            if observed_days<3 or pax<10 or scheduled_days<4 or crossings<=0 or hold[2]<=0:continue
            group=(route,a,b);groups[group][0][hour]=pax/crossings;groups[group][1][hour]=hold[0]/hold[2]
        for group,(train,target) in groups.items():
            if len(train)<3 or len(set(train.values()))<2:continue
            counts['groups']+=1;counts['hours']+=len(train)
            counts.update(compare_group(train,target))
            for hour in train:counts['covered_target_sample_passenger_segments']+=cells[(*group,hour)][held][0]
        decisive=counts['concordant']+counts['discordant']
        folds.append({'held_out_start':start,'held_out_end':end,**dict(counts),
                      'decisive_pair_concordance':counts['concordant']/decisive if decisive else None,
                      'matched_target_passenger_segment_coverage':counts['covered_target_sample_passenger_segments']/counts['target_sample_passenger_segments'] if counts['target_sample_passenger_segments'] else None})
    return {'folds':folds,'excluded':dict(excluded),'limitations':'Weekday only: the production weekend rule requires three observed days, impossible in two training weeks. Holidays remain included. Scheduled zero samples assume complete ingestion. Fold training sets overlap and pairs are correlated. This assesses ticket samples, not occupancy; no October 25–31 records read.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('records','gtfs','output'):p.add_argument('--'+k,required=True)
    a=p.parse_args();out=Path(a.output)
    if out.exists():raise FileExistsError('Refusing to overwrite report')
    result=evaluate(a.records,a.gtfs)
    with out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2))
