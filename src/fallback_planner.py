"""Simplified mapped journeys from the built-in timetable planner, for use without OTP.

Results use the same itinerary shape as the OTP endpoint so the API summaries
and the screen work unchanged. Routing is limited to direct buses and changes
at the same GTFS stop ID; walking to and from stops is a straight-line
estimate, not a street route.
"""
from datetime import datetime, timedelta
from math import asin, cos, radians, sin, sqrt
from journeys import IST
from otp_client import journey_crowding_summary, signal_coverage, timing_breakdown, transfer_walks_within_limit, validate_request
from predict import model_timing_basis, query

WALK_METRES_PER_MINUTE = 75     # about 4.5 km/h
DETOUR_FACTOR = 1.3             # straight line to street distance, a common planning assumption
MAX_ACCESS_METRES = 800
CANDIDATE_STOPS = 8             # nearest stops are often served by other routes; see tests
LIMITATIONS = ('Simplified routing without OpenTripPlanner: direct buses and changes at the same stop only. '
               'Walking to and from stops is a straight-line estimate, not a street route. Times use the timetable. '
               'Ticket signals are not occupancy.')


def metres_between(a, b):
    lat1, lon1, lat2, lon2 = map(radians, (a[0], a[1], b[0], b[1]))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371000 * asin(sqrt(h))


def nearby_stops(planner, point, radius=MAX_ACCESS_METRES, limit=CANDIDATE_STOPS):
    found = sorted((metres_between(point, coords), stop) for stop, coords in planner.stop_coordinates.items())
    return [(stop, distance) for distance, stop in found if distance <= radius][:limit]


def _place(planner, stop=None, point=None, name=None):
    if stop is not None:
        lat, lon = planner.stop_coordinates.get(stop, (None, None))
        return {'name': planner.stops.get(stop, ''), 'lat': lat, 'lon': lon, 'stop': {'gtfsId': 'gtfs:' + stop}}
    return {'name': name, 'lat': point[0], 'lon': point[1], 'stop': None}


def _walk(start, distance, origin, destination):
    end = start + timedelta(minutes=distance * DETOUR_FACTOR / WALK_METRES_PER_MINUTE)
    return {'mode': 'WALK', 'distance': round(distance * DETOUR_FACTOR), 'distance_basis': 'straight-line estimate',
            'start': {'scheduledTime': start.isoformat()}, 'end': {'scheduledTime': end.isoformat()},
            'from': origin, 'to': destination}, end


class FallbackPlanner:
    def __init__(self, planner):
        self.planner = planner
        self.sequences = planner.sequences

    def _signals(self, route, seq, i, j, midnight):
        timing_basis = model_timing_basis(self.planner.database)
        boarding = midnight + timedelta(seconds=seq[i][3])
        signals = []
        for k in range(i, j):
            crossing = midnight + timedelta(seconds=seq[k][3])
            lookup = boarding if timing_basis == 'boarding' else crossing
            signal = query(self.planner.database, route, seq[k][1], seq[k + 1][1], lookup.isoformat())
            signals.append({'from_stop_id': seq[k][1], 'to_stop_id': seq[k + 1][1], 'scheduled_time': crossing.isoformat(),
                            'model_lookup_time': lookup.isoformat(), 'model_timing_basis': timing_basis,
                            'status': signal['status'], 'all_scheduled_days_proxy': signal.get('all_scheduled_days_proxy'),
                            'relative_crowding': signal.get('relative_crowding'), 'schedule_alignment': signal.get('schedule_alignment')})
        return signals

    def _bus_leg(self, route, trip, origin, destination, departure):
        """Build a bus leg for the scheduled trip departing `origin` at `departure`."""
        seq = self.sequences.get(trip)
        if not seq:
            return None
        for i, stop in enumerate(seq):
            midnight = departure - timedelta(seconds=stop[3])
            if stop[1] != origin or midnight.time() != datetime.min.time():
                continue
            for j in range(i + 1, len(seq)):
                if seq[j][1] == destination:
                    arrival = midnight + timedelta(seconds=seq[j][2])
                    return {'mode': 'BUS', 'distance': None, 'serviceDate': midnight.date().isoformat(),
                            'start': {'scheduledTime': departure.isoformat()}, 'end': {'scheduledTime': arrival.isoformat()},
                            'from': _place(self.planner, origin), 'to': _place(self.planner, destination),
                            'route': {'shortName': route, 'gtfsId': None}, 'trip': {'gtfsId': 'gtfs:' + trip},
                            'intermediateStops': [{'gtfsId': 'gtfs:' + s[1]} for s in seq[i + 1:j]],
                            'v1_signals': self._signals(route, seq, i, j, midnight),
                            'v1_signal_status': 'attached; availability varies by segment'}
        return None

    def _itinerary(self, requested, start_point, end_point, first_stop, first_distance, last_stop, last_distance, buses):
        legs, prior = [], requested
        if first_distance > 30:
            walk, prior = _walk(requested, first_distance, _place(self.planner, point=start_point, name='Start'), _place(self.planner, first_stop))
            legs.append(walk)
        if datetime.fromisoformat(buses[0]['start']['scheduledTime']) < prior:
            return None
        legs.extend(buses)
        if last_distance > 30:
            walk, _ = _walk(datetime.fromisoformat(buses[-1]['end']['scheduledTime']), last_distance,
                            _place(self.planner, last_stop), _place(self.planner, point=end_point, name='Destination'))
            legs.append(walk)
        walk_total = sum(leg['distance'] for leg in legs if leg['mode'] == 'WALK')
        return {'start': legs[0]['start']['scheduledTime'], 'end': legs[-1]['end']['scheduledTime'],
                'walkDistance': walk_total, 'numberOfTransfers': len(buses) - 1, 'legs': legs}

    def plan(self, lat1, lon1, lat2, lon2, departure, max_transfer_walk=1000, limit=8):
        coords, when, walk_limit = validate_request(lat1, lon1, lat2, lon2, departure, max_transfer_walk)
        requested = when.astimezone(IST)
        start_point, end_point = (coords[0], coords[1]), (coords[2], coords[3])
        origins, destinations = nearby_stops(self.planner, start_point), nearby_stops(self.planner, end_point)
        found = []
        for first_stop, first_distance in origins:
            for last_stop, last_distance in destinations:
                if first_stop == last_stop:
                    continue
                # Leave time to walk to the stop before looking for buses.
                earliest = requested + timedelta(minutes=first_distance * DETOUR_FACTOR / WALK_METRES_PER_MINUTE)
                for option in self.planner.journeys(first_stop, last_stop, earliest.isoformat())['journeys']:
                    leg = self._bus_leg(option['route'], option['trip_id'], first_stop, last_stop,
                                        datetime.fromisoformat(option['scheduled_departure']))
                    if leg:
                        found.append((first_stop, first_distance, last_stop, last_distance, [leg]))
        if origins and destinations and not any(len(f[4]) == 1 for f in found):
            # Same-stop transfers are slow to search, so try only the closest stop pair.
            (first_stop, first_distance), (last_stop, last_distance) = origins[0], destinations[0]
            if first_stop != last_stop:
                earliest = requested + timedelta(minutes=first_distance * DETOUR_FACTOR / WALK_METRES_PER_MINUTE)
                for option in self.planner.transfer_journeys(first_stop, last_stop, earliest.isoformat())['journeys']:
                    legs = [self._bus_leg(l['route'], l['trip_id'], l['from_stop_id'], l['to_stop_id'],
                                          datetime.fromisoformat(l['scheduled_departure'])) for l in option['legs']]
                    if all(legs):
                        found.append((first_stop, first_distance, last_stop, last_distance, legs))
        itineraries, seen = [], set()
        for first_stop, first_distance, last_stop, last_distance, buses in found:
            key = tuple((leg['trip']['gtfsId'], leg['start']['scheduledTime']) for leg in buses)
            if key in seen:
                continue
            seen.add(key)
            item = self._itinerary(requested, start_point, end_point, first_stop, first_distance, last_stop, last_distance, buses)
            if item and transfer_walks_within_limit(item['legs'], walk_limit):
                itineraries.append(item)
        itineraries.sort(key=lambda item: (item['end'], item['walkDistance']))
        itineraries = itineraries[:limit]
        for item in itineraries:
            timing_breakdown(item, requested)
            signal_coverage(item)
            journey_crowding_summary(item)
        return {'journeys': itineraries, 'max_transfer_walk_metres': walk_limit, 'routing_source': 'built-in',
                'nearby_stops_considered': {'origin': len(origins), 'destination': len(destinations)},
                'limitations': LIMITATIONS}
