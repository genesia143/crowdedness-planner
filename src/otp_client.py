"""Backend integration with an independently running OpenTripPlanner graph."""
import json
import math
from datetime import datetime
from urllib.request import Request, urlopen
from otp_adapter import annotate_v1, transfer_walks_within_limit

QUERY = '''query($lat1:CoordinateValue!,$lon1:CoordinateValue!,$lat2:CoordinateValue!,$lon2:CoordinateValue!,$when:OffsetDateTime!) {
 planConnection(origin:{location:{coordinate:{latitude:$lat1,longitude:$lon1}}}, destination:{location:{coordinate:{latitude:$lat2,longitude:$lon2}}}, dateTime:{earliestDeparture:$when}, modes:{direct:[WALK],transit:{transit:[{mode:BUS}]}}) {
 edges { node { start end walkDistance numberOfTransfers legs { mode distance serviceDate start { scheduledTime } trip { gtfsId } intermediateStops { gtfsId } from { name lat lon stop { gtfsId } } to { name lat lon stop { gtfsId } } route { shortName gtfsId } } } } } }'''


def plan(endpoint, gtfs, database, lat1, lon1, lat2, lon2, departure, max_transfer_walk=1000):
    coords = [float(v) for v in (lat1, lon1, lat2, lon2)]
    if not all(math.isfinite(x) for x in coords) or not all(-90 <= coords[i] <= 90 for i in (0,2)) or not all(-180 <= coords[i] <= 180 for i in (1,3)):
        raise ValueError('invalid coordinates')
    when = datetime.fromisoformat(departure.replace('Z', '+00:00'))
    if when.utcoffset() is None:
        raise ValueError('departure must include a timezone offset')
    limit = float(max_transfer_walk)
    if not math.isfinite(limit) or not 0 <= limit <= 10000:
        raise ValueError('max_transfer_walk must be between 0 and 10000 metres')
    variables = dict(zip(('lat1','lon1','lat2','lon2'), coords))
    variables['when'] = when.isoformat()
    request = Request(endpoint, data=json.dumps({'query':QUERY, 'variables':variables}).encode(), headers={'Content-Type':'application/json'})
    with urlopen(request, timeout=90) as response:
        data = json.load(response)
    if data.get('errors') or not (data.get('data') or {}).get('planConnection'):
        raise RuntimeError('OpenTripPlanner could not plan the journey')
    candidates = [edge['node'] for edge in data['data']['planConnection']['edges']]
    bus = [item for item in candidates if any(leg.get('mode') == 'BUS' for leg in item.get('legs', []))]
    accepted = [item for item in bus if transfer_walks_within_limit(item['legs'], limit)]
    if accepted:
        # Scan the GTFS stop-times file once for all returned itineraries.
        annotate_v1({'legs': [leg for item in accepted for leg in item['legs']]}, gtfs, database)
    return {'journeys':accepted, 'max_transfer_walk_metres':limit, 'returned_candidates':len(candidates), 'excluded_bus_candidates':len(bus)-len(accepted), 'limitations':'Transfer walking limit is applied after routing, so suitable alternatives may be omitted. Walking uses OpenStreetMap and depends on graph coverage. Ticket signals are not occupancy.'}
