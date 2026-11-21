"""Backend integration with an independently running OpenTripPlanner graph."""
import json
import math
from datetime import datetime
from urllib.request import Request, urlopen
from otp_adapter import annotate_v1, transfer_walks_within_limit

QUERY = '''query($lat1:CoordinateValue!,$lon1:CoordinateValue!,$lat2:CoordinateValue!,$lon2:CoordinateValue!,$when:OffsetDateTime!) {
 planConnection(origin:{location:{coordinate:{latitude:$lat1,longitude:$lon1}}}, destination:{location:{coordinate:{latitude:$lat2,longitude:$lon2}}}, dateTime:{earliestDeparture:$when}, modes:{direct:[WALK],transit:{transit:[{mode:BUS}]}}) {
 edges { node { start end walkDistance numberOfTransfers legs { mode distance serviceDate start { scheduledTime } end { scheduledTime } trip { gtfsId } intermediateStops { gtfsId } from { name lat lon stop { gtfsId } } to { name lat lon stop { gtfsId } } route { shortName gtfsId } } } } } }'''



def timing_breakdown(itinerary, requested):
    """Report scheduled leg durations and gaps; preserve unknown timing as null."""
    def parse(value):
        try:
            result = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return result if result.utcoffset() is not None else None
        except (AttributeError, TypeError, ValueError):
            return None
    legs = itinerary.get('legs', [])
    prior = requested
    waits = []
    walking = 0.0
    riding = 0.0
    valid = True
    for leg in legs:
        start = parse((leg.get('start') or {}).get('scheduledTime'))
        end = parse((leg.get('end') or {}).get('scheduledTime'))
        if start is None or end is None or end < start or prior is None or start < prior:
            valid = False
            prior = end
            leg['duration_minutes'] = None
            continue
        gap = (start - prior).total_seconds() / 60
        if gap:
            waits.append({'before_mode': leg.get('mode'), 'minutes': gap})
        duration = (end - start).total_seconds() / 60
        leg['duration_minutes'] = duration
        if leg.get('mode') == 'WALK': walking += duration
        elif leg.get('mode') == 'BUS': riding += duration
        else: valid = False
        prior = end
    itinerary['timing_summary'] = {
        'walking_minutes': walking if valid else None,
        'bus_minutes': riding if valid else None,
        'waiting_minutes': sum(x['minutes'] for x in waits) if valid else None,
        'waiting_periods': waits,
        'status': 'available' if valid else 'incomplete or inconsistent leg times',
        'basis': 'Scheduled times, including waiting from requested departure; not live predictions.'
    }


def signal_coverage(itinerary):
    """Summarise model coverage without inventing a journey crowding score."""
    bus_legs = [leg for leg in itinerary.get('legs', []) if leg.get('mode') == 'BUS']
    signals = [signal for leg in bus_legs for signal in leg.get('v1_signals', [])]
    matched = sum(signal.get('status') == 'available' and
                  signal.get('all_scheduled_days_proxy') is not None for signal in signals)
    incomplete_legs = sum(not leg.get('v1_signals') for leg in bus_legs)
    itinerary['signal_coverage'] = {
        'segments_with_observations_and_service': matched,
        'segments_without_observations_or_service': len(signals) - matched,
        'bus_legs_without_segment_details': incomplete_legs,
        'basis': 'Ticket-sample signal coverage; not an occupancy or crowding estimate.'
    }


def journey_crowding_summary(itinerary):
    """Describe segment labels, without combining incomparable route baselines."""
    labels = ('likely quieter', 'typical', 'likely busier')
    legs = []
    for index, leg in enumerate(itinerary.get('legs', [])):
        if leg.get('mode') != 'BUS':
            continue
        signals = leg.get('v1_signals') or []
        counts = {label: 0 for label in labels}
        unknown = 0
        broader = 0
        for signal in signals:
            comparison = signal.get('relative_crowding') or {}
            label = comparison.get('label')
            fallback = comparison.get('evidence_tier') == 'broader_window'
            if (signal.get('status') == 'available' or fallback) and label in counts:
                counts[label] += 1
                broader += int(fallback)
            else:
                unknown += 1
        legs.append({
            'leg_index': index,
            'route': (leg.get('route') or {}).get('shortName'),
            'labelled_segments': sum(counts.values()),
            'segments_without_label': unknown,
            'segment_details_available': bool(signals),
            'segment_label_counts': counts,
            'broader_window_segments': broader,
        })
    known = sum(leg['labelled_segments'] for leg in legs)
    missing = sum(leg['segments_without_label'] for leg in legs)
    missing_legs = sum(not leg['segment_details_available'] for leg in legs)
    if not known:
        status = 'insufficient evidence'
    elif missing or missing_legs:
        status = 'partial evidence'
    else:
        status = 'labelled segments available'
    busier = sum(leg['segment_label_counts']['likely busier'] for leg in legs)
    if busier:
        headline = 'Some stretches busier than usual'
    elif not known or missing or missing_legs:
        headline = 'Limited crowding information'
    else:
        headline = 'No busier-than-usual stretches identified'
    itinerary['crowding_summary'] = {
        'status': status,
        'headline': headline,
        'busier_segments': busier,
        'labelled_segments': known,
        'broader_window_segments': sum(leg['broader_window_segments'] for leg in legs),
        'segments_without_label': missing,
        'bus_legs_without_segment_details': missing_legs,
        'bus_legs': legs,
        'provisional': True,
        'interpretation': 'Labels compare each route segment with its own hours on the same day type. Counts are not a journey-level crowding score and cannot compare different routes or segments. Missing details are not quiet segments; the labels are not measured occupancy.',
    }


def validate_request(lat1, lon1, lat2, lon2, departure, max_transfer_walk=1000):
    """Check mapped-journey inputs; shared by OTP and the built-in fallback."""
    try:
        coords = [float(v) for v in (lat1, lon1, lat2, lon2)]
    except (TypeError, ValueError):
        raise ValueError('invalid coordinates')
    if not all(math.isfinite(x) for x in coords) or not all(-90 <= coords[i] <= 90 for i in (0,2)) or not all(-180 <= coords[i] <= 180 for i in (1,3)):
        raise ValueError('invalid coordinates')
    when = datetime.fromisoformat(departure.replace('Z', '+00:00'))
    if when.utcoffset() is None:
        raise ValueError('departure must include a timezone offset')
    try:
        limit = float(max_transfer_walk)
    except (TypeError, ValueError):
        raise ValueError('max_transfer_walk must be between 0 and 10000 metres')
    if not math.isfinite(limit) or not 0 <= limit <= 10000:
        raise ValueError('max_transfer_walk must be between 0 and 10000 metres')
    return coords, when, limit


def fetch_otp(endpoint, variables):
    request = Request(endpoint, data=json.dumps({'query':QUERY, 'variables':variables}).encode(), headers={'Content-Type':'application/json'})
    with urlopen(request, timeout=90) as response:
        return json.load(response)


class RecordedOTP:
    """Replay raw OTP responses saved by scripts/record_fixtures.py.

    Matches on rounded coordinates and the exact departure; raises LookupError
    when no recording exists so the caller can fall back.
    """
    def __init__(self, directory):
        from pathlib import Path
        self.directory = Path(directory)
        manifest = json.loads((self.directory / 'manifest.json').read_text(encoding='utf-8'))
        # The recorder writes origin/destination; from/to is accepted for hand-written manifests.
        self.cases = {self.key(*case.get('origin', case.get('from')), *case.get('destination', case.get('to')), case['departure']): case['id']
                      for case in manifest['cases']}

    @staticmethod
    def key(lat1, lon1, lat2, lon2, when):
        moment = datetime.fromisoformat(str(when).replace('Z', '+00:00'))
        return tuple(round(float(v), 5) for v in (lat1, lon1, lat2, lon2)) + (moment.isoformat(),)

    def __call__(self, endpoint, variables):
        case = self.cases.get(self.key(variables['lat1'], variables['lon1'], variables['lat2'], variables['lon2'], variables['when']))
        if case is None:
            raise LookupError('no recorded OTP response for this request')
        return json.loads((self.directory / 'otp' / (case + '.json')).read_text(encoding='utf-8'))


def plan(endpoint, gtfs, database, lat1, lon1, lat2, lon2, departure, max_transfer_walk=1000, fetch=fetch_otp, stop_times=None):
    coords, when, limit = validate_request(lat1, lon1, lat2, lon2, departure, max_transfer_walk)
    variables = dict(zip(('lat1','lon1','lat2','lon2'), coords))
    variables['when'] = when.isoformat()
    data = fetch(endpoint, variables)
    if data.get('errors') or not (data.get('data') or {}).get('planConnection'):
        raise RuntimeError('OpenTripPlanner could not plan the journey')
    candidates = [edge['node'] for edge in data['data']['planConnection']['edges']]
    bus = [item for item in candidates if any(leg.get('mode') == 'BUS' for leg in item.get('legs', []))]
    accepted = [item for item in bus if transfer_walks_within_limit(item['legs'], limit)]
    for item in accepted:
        timing_breakdown(item, when)
    if accepted:
        # Look up stop times once for all returned itineraries: from memory when the API has a planner, else from the file.
        annotate_v1({'legs': [leg for item in accepted for leg in item['legs']]}, gtfs, database, stop_times=stop_times)
        for item in accepted:
            signal_coverage(item)
            journey_crowding_summary(item)
    return {'journeys':accepted, 'max_transfer_walk_metres':limit, 'returned_candidates':len(candidates), 'excluded_bus_candidates':len(bus)-len(accepted), 'limitations':'Transfer walking limit is applied after routing, so suitable alternatives may be omitted. Walking uses OpenStreetMap and depends on graph coverage. Ticket signals are not occupancy.'}
