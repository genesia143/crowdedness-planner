#!/usr/bin/env python3
"""Compare standard OTP results with its filter-debug results for one journey."""
import argparse
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from otp_client import QUERY
from otp_adapter import transfer_walks_within_limit


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--endpoint', default='http://localhost:18080/otp/gtfs/v1')
    p.add_argument('--from-lat',type=float,required=True);p.add_argument('--from-lon',type=float,required=True)
    p.add_argument('--to-lat',type=float,required=True);p.add_argument('--to-lon',type=float,required=True)
    p.add_argument('--departure',required=True);p.add_argument('--max-transfer-walk',type=float,default=1000)
    args=p.parse_args()
    variables={'lat1':args.from_lat,'lon1':args.from_lon,'lat2':args.to_lat,'lon2':args.to_lon,'when':args.departure}
    def run(debug):
        query=QUERY.replace('dateTime:{earliestDeparture:$when}', 'itineraryFilter:{itineraryFilterDebugProfile:LIST_ALL}, dateTime:{earliestDeparture:$when}') if debug else QUERY
        query = query.replace('node { start end', 'node { systemNotices { tag text } start end')
        req=Request(args.endpoint,data=json.dumps({'query':query,'variables':variables}).encode(),headers={'Content-Type':'application/json'})
        with urlopen(req,timeout=90) as response: result=json.load(response)
        if result.get('errors'): raise RuntimeError(result['errors'])
        return [e['node'] for e in result['data']['planConnection']['edges']]
    def signature(item):
        return json.dumps([(l['mode'],l.get('trip'),l.get('from'),l.get('to'),l.get('start')) for l in item['legs']],sort_keys=True)
    standard, debug = run(False), run(True)
    standard_ids={signature(x) for x in standard}
    extra=[x for x in debug if signature(x) not in standard_ids and any(l['mode']=='BUS' for l in x['legs'])]
    within=[x for x in extra if transfer_walks_within_limit(x['legs'],args.max_transfer_walk)]
    print(json.dumps({'standard_results':len(standard),'debug_results':len(debug),'additional_bus_results':len(extra),'additional_bus_results_within_transfer_limit':len(within),'additional_candidate_notices':[x.get('systemNotices',[]) for x in within],'interpretation':'Debug may include filtered or otherwise unsuitable itineraries; inspect notices and feasibility before use.'},indent=2))

if __name__=='__main__': main()
