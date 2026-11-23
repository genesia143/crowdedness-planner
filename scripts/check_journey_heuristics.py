"""Compare fastest-journey proxy at fixed places and times; no ticket reads."""
import json
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PAIRS = {
    'Kashmere Gate to Nehru Place': ((28.668198,77.229219),(28.5487,77.256981)),
    'Anand Vihar to Shivaji Stadium': ((28.648875,77.318377),(28.6323,77.2165)),
    'Rajouri Garden to Nehru Place': ((28.648433,77.120783),(28.548576,77.249133)),
    'Lajpat Nagar to Hauz Khas': ((28.56661,77.246373),(28.543389,77.20754)),
}
TIMES = {'weekday_peak':'2026-11-02T08:00:00+05:30', 'weekday_offpeak':'2026-11-02T13:00:00+05:30',
         'saturday_peak':'2026-11-07T08:00:00+05:30', 'sunday_peak':'2026-11-08T08:00:00+05:30'}

def check(item):
    name, period = item
    a, b = PAIRS[name]
    query = urllib.parse.urlencode({'from_lat':a[0],'from_lon':a[1],'to_lat':b[0],'to_lon':b[1],
                                    'departure':TIMES[period], 'max_transfer_walk':1000, 'extra_minutes':20})
    try:
        with urllib.request.urlopen('http://127.0.0.1:8776/journeys/mapped?' + query, timeout=180) as r:
            data=json.load(r)
        index=data.get('choices',{}).get('fastest_index')
        journey=data['journeys'][index] if index is not None else None
        return {'pair':name,'period':period,'routing_source':data.get('routing_source'),
                'pressure':journey.get('journey_pressure') if journey else None,
                'routes':[(leg.get('route') or {}).get('shortName') for leg in journey.get('legs',[]) if leg.get('mode')=='BUS'] if journey else []}
    except Exception as error:
        return {'pair':name,'period':period,'error':str(error)}

with ThreadPoolExecutor(max_workers=4) as pool:
    results=list(pool.map(check, [(name,period) for name in PAIRS for period in TIMES]))
Path('data/otp-trial/journey-heuristic-check.json').write_text(json.dumps(results,indent=2), encoding='utf-8')
for row in results:
    print(row['pair'],row['period'],row.get('routes'),row.get('pressure'),row.get('error'))
