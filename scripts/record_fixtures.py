"""Record routing and API fixtures from a running local OTP and planner API.

Uses only the specified routing dates, the configured model and GTFS; never reads
raw tickets. Verify that the running services use the files supplied below.
"""
import csv
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, 'src')
from otp_client import QUERY

OTP = 'http://127.0.0.1:18080/otp/gtfs/v1'
API = 'http://127.0.0.1:8766'
GTFS = Path('data/otp-trial/gtfs-original')
FEED_ZIP = Path('data/otp-trial/india-crop/delhi-gtfs.zip')
GRAPH = Path('data/otp-trial/india-crop/graph.obj')
OSM = Path('data/otp-trial/india-crop/delhi-ncr.osm.pbf')
MODEL = Path('data/otp-trial/model-v1-split-days.db')
OUT = Path('tests/fixtures/otp')
CASES = [
 ('01_kg_np_thu_0830','1025','2560','2026-10-22T08:30',1000),
 ('02_kg_np_thu_2300','1025','2560','2026-10-22T23:00',1000),
 ('03_av_cp_thu_1800','917','365','2026-10-22T18:00',1000),
 ('04_av_cp_thu_1820','917','365','2026-10-22T18:20',1000),
 ('05_av_cp_thu_1840','917','365','2026-10-22T18:40',1000),
 ('06_av_cp_sat_1800','917','365','2026-10-24T18:00',1000),
 ('07_av_cp_sun_1800','917','365','2026-11-01T18:00',1000),
 ('08_ln_hk_thu_0900','8299','2378','2026-10-22T09:00',1000),
 ('09_rg_np_thu_0900','2707','2559','2026-10-22T09:00',1000),
 ('10_rg_np_thu_0900_walk0','2707','2559','2026-10-22T09:00',0),
 ('11_dw_mh_thu_0800','7544','7908','2026-10-22T08:00',1000),
 ('12_nr_kg_thu_0730','319','1025','2026-10-22T07:30',1000),
 ('13_br_md_thu_0800','9785','9792','2026-10-22T08:00',1000),
 ('14_place_to_place',(28.6129,77.2295),(28.5286,77.2190),'2026-10-22T10:00',1000),
 ('15_no_service_0300','1025','2560','2026-10-22T03:00',1000),
]

def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()

def save(path, value):
    path = OUT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')

def request(url, data=None):
    req = Request(url, data=data, headers={'Content-Type':'application/json'} if data else {})
    try:
        with urlopen(req, timeout=180) as r: return r.status, json.load(r)
    except HTTPError as e: return e.code, json.load(e)

def get(path, params):
    return request(API + path + '?' + urlencode(params))

def main():
    if OUT.exists() and any(OUT.iterdir()):
        raise SystemExit('Output directory is not empty; refusing to overwrite recordings')
    with (GTFS / 'stops.txt').open(encoding='utf-8-sig', newline='') as f:
        stops = {r['stop_id']:r for r in csv.DictReader(f)}
    def point(item):
        if not isinstance(item, str): return item
        row = stops[item]
        return (float(row['stop_lat']), float(row['stop_lon']))
    manifest = {'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
                'git_commit':subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
                'otp_version':'2.7.0', 'osm_extract':'Geofabrik India extract cropped to Delhi region; local source file dated 2026-11-21',
                'input_sha256': {str(p):sha256(p) for p in (FEED_ZIP, GRAPH, OSM, MODEL)},
                'warning':'Input hashes describe the files configured when recording; they do not independently prove running process provenance.',
                'cases':[]}
    first_signal = None
    for cid, a, b, when, walk in CASES:
        (lat1,lon1),(lat2,lon2) = point(a),point(b)
        departure = when+':00+05:30'
        variables = dict(lat1=lat1,lon1=lon1,lat2=lat2,lon2=lon2,when=departure)
        t=time.monotonic(); raw_status,raw=request(OTP,json.dumps({'query':QUERY,'variables':variables}).encode()); otp_s=round(time.monotonic()-t,2)
        save('otp/'+cid+'.json',raw)
        params=dict(from_lat=lat1,from_lon=lon1,to_lat=lat2,to_lon=lon2,departure=departure,max_transfer_walk=walk)
        t=time.monotonic(); status,body=get('/journeys/mapped',params); api_s=round(time.monotonic()-t,2)
        save('api/'+cid+'.json',{'status':status,'body':body})
        manifest['cases'].append(dict(id=cid,from_stop_id=a if isinstance(a,str) else None,to_stop_id=b if isinstance(b,str) else None,origin=[lat1,lon1],destination=[lat2,lon2],departure=departure,max_transfer_walk=walk,otp_status=raw_status,otp_errors=raw.get('errors'),api_status=status,journeys=len(body.get('journeys',[])),otp_seconds=otp_s,api_seconds=api_s))
        if first_signal is None:
            for journey in body.get('journeys',[]):
                for leg in journey.get('legs',[]):
                    for sig in leg.get('v1_signals',[]):
                        if sig.get('status') == 'available': first_signal=(sig,departure,(leg.get('route') or {}).get('shortName')); break
                    if first_signal: break
                if first_signal: break
        print(cid, 'OTP',raw_status,'API',status,'journeys',len(body.get('journeys',[])),flush=True)
    for name,path,params in [('stops_nehru','/stops',{'q':'nehru'}),('bad_departure','/journeys/mapped',dict(from_lat=28.6,from_lon=77.2,to_lat=28.5,to_lon=77.2,departure='2026-10-22T09:00:00'))]:
        status,body=get(path,params); save('api/'+name+'.json',{'status':status,'body':body,'request':{'path':path,'params':params}})
    if first_signal:
        sig,departure,route=first_signal
        params=dict(route=route,from_stop_id=sig['from_stop_id'],to_stop_id=sig['to_stop_id'],departure=departure)
        status,body=get('/segments/signal',params); save('api/segment_signal.json',{'status':status,'body':body,'request':{'path':'/segments/signal','params':params}})
    else: raise RuntimeError('No available segment signal found in recorded journeys')
    manifest['files_sha256']={str(p.relative_to(OUT)):sha256(p) for p in sorted(OUT.rglob('*.json'))}
    save('manifest.json',manifest)
    print('Completed recording',flush=True)

if __name__ == '__main__': main()
