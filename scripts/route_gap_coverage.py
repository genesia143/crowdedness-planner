"""Summarise development-period ticket segment samples without same-hour service."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from service import scheduled_crossings


def calculate(data, schedule):
    start,end=data['training_start'],data['training_end']
    if start<'2026-10-22' or end>'2026-10-24' or end<start:
        raise ValueError('Only October 22–24 tuning data is allowed')
    routes=defaultdict(lambda:{'sample_passenger_segments':0,'without_same_hour_service':0,'cells':0,'cells_without_same_hour_service':0})
    for row in data['records']:
        if not start<=row['date']<=end: raise ValueError('Record outside declared period')
        key=(row['route'],row['from_stop_id'],row['to_stop_id'],row['date'],row['hour'],row['day_type'])
        item=routes[row['route']];item['sample_passenger_segments']+=row['passengers'];item['cells']+=1
        if key not in schedule:
            item['without_same_hour_service']+=row['passengers'];item['cells_without_same_hour_service']+=1
    return {route:{**v,'sample_weight_gap_rate':v['without_same_hour_service']/v['sample_passenger_segments'] if v['sample_passenger_segments'] else None} for route,v in routes.items()}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--validation',required=True);p.add_argument('--gtfs',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    data=json.loads(Path(a.validation).read_text());start,end=data['training_start'],data['training_end']
    if start<'2026-10-22' or end>'2026-10-24' or end<start: raise ValueError('Only October 22–24 tuning data is allowed')
    result=calculate(data,scheduled_crossings(a.gtfs,start,end))
    with Path(a.output).open('x') as f:json.dump(result,f,indent=2)
    print('Routes:',len(result),'output:',a.output)
