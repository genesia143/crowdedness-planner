"""Query a running local OTP 2.7 trial; inspect walking distances and bus legs."""
import argparse
import json
import urllib.request

QUERY = '''query($lat1:CoordinateValue!,$lon1:CoordinateValue!,$lat2:CoordinateValue!,$lon2:CoordinateValue!,$when:OffsetDateTime!) {
  planConnection(origin:{location:{coordinate:{latitude:$lat1,longitude:$lon1}}},
    destination:{location:{coordinate:{latitude:$lat2,longitude:$lon2}}},
    dateTime:{earliestDeparture:$when}, modes:{direct:[WALK],transit:{transit:[{mode:BUS}]}}) {
    edges { node { start end walkDistance numberOfTransfers legs { mode distance serviceDate start { scheduledTime } trip { gtfsId } intermediateStops { gtfsId } from { name lat lon stop { gtfsId } } to { name lat lon stop { gtfsId } } route { shortName gtfsId } } } }
  }
}'''
CASES = {
 'badarpur': (28.49313012,77.30372712,28.49322334,77.30304927),
 'dhansa': (28.6115929,76.9778599,28.611491,76.97791),
 '307down': (28.60342055,77.30234208,28.64388636,77.22437294),
 'cross_city': (28.60342055,77.30234208,28.49313012,77.30372712),
}

def run(endpoint, when):
    output={}
    for name,(lat1,lon1,lat2,lon2) in CASES.items():
        payload=json.dumps({'query':QUERY,'variables':{'lat1':lat1,'lon1':lon1,'lat2':lat2,'lon2':lon2,'when':when}}).encode()
        request=urllib.request.Request(endpoint,data=payload,headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=90) as response: result=json.load(response)
        output[name]=result
    return output

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--endpoint',default='http://localhost:18080/otp/gtfs/v1');p.add_argument('--when',default='2026-10-22T08:00:00+05:30');p.add_argument('--output',required=True);a=p.parse_args()
    results=run(a.endpoint,a.when)
    with open(a.output,'w',encoding='utf-8') as f:json.dump(results,f,indent=2)
    for name,result in results.items():
        print(name,'errors',result.get('errors',[]),'itineraries',len((result.get('data') or {}).get('planConnection',{}).get('edges',[])))
