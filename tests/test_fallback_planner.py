import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from api import mapped_journeys
from fallback_planner import FallbackPlanner, metres_between
from journeys import JourneyPlanner
from otp_client import RecordedOTP
from predict import create_database

DEFINITION = 'observed ticket-sample passenger journeys crossing a segment, grouped by ticket boarding hour'


def write(path, fields, values):
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(values)


def network(p):
    """Stops a-b-c on route 1UP, about 1 km apart, and c-d on route 2UP."""
    stops = [('a', 28.600, 77.200), ('b', 28.609, 77.200), ('c', 28.618, 77.200), ('d', 28.627, 77.200)]
    write(p/'stops.txt', ['stop_id','stop_name','stop_lat','stop_lon'], [{'stop_id':s,'stop_name':s.upper(),'stop_lat':lat,'stop_lon':lon} for s, lat, lon in stops])
    write(p/'routes.txt', ['route_id','route_short_name'], [{'route_id':'r1','route_short_name':'1UP'}, {'route_id':'r2','route_short_name':'2UP'}])
    write(p/'trips.txt', ['trip_id','route_id','service_id'], [{'trip_id':'t1','route_id':'r1','service_id':'s'}, {'trip_id':'t2','route_id':'r2','service_id':'s'}])
    times = [('t1','a','09:00:00'), ('t1','b','09:10:00'), ('t1','c','09:20:00'), ('t2','c','09:30:00'), ('t2','d','09:40:00')]
    write(p/'stop_times.txt', ['trip_id','stop_sequence','stop_id','arrival_time','departure_time'],
          [{'trip_id':t,'stop_sequence':i,'stop_id':s,'arrival_time':time,'departure_time':time} for i, (t, s, time) in enumerate(times)])
    write(p/'calendar.txt', ['service_id','monday','tuesday','wednesday','thursday','friday','saturday','sunday','start_date','end_date'],
          [{'service_id':'s','monday':1,'tuesday':1,'wednesday':1,'thursday':1,'friday':1,'saturday':1,'sunday':1,'start_date':'20261001','end_date':'20261031'}])
    (p/'data.json').write_text(json.dumps({'training_start':'2026-10-01','training_end':'2026-10-21','definition':DEFINITION,'quality':{},'records':[]}))
    create_database(p/'data.json', p/'model.db', gtfs=p)
    return JourneyPlanner(p, p/'model.db')


class FallbackPlannerTests(unittest.TestCase):
    def test_direct_journey_has_walks_timing_and_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            planner = FallbackPlanner(network(Path(tmp)))
            # Start about 220 m south of stop a; finish at stop c.
            result = planner.plan(28.598, 77.200, 28.618, 77.200, '2026-10-22T08:50:00+05:30')
            self.assertEqual(result['routing_source'], 'built-in')
            journey = result['journeys'][0]
            self.assertEqual([leg['mode'] for leg in journey['legs']], ['WALK', 'BUS'])
            self.assertEqual(journey['legs'][1]['route']['shortName'], '1UP')
            self.assertEqual(journey['numberOfTransfers'], 0)
            self.assertEqual(journey['legs'][0]['distance'], round(metres_between((28.598, 77.2), (28.6, 77.2)) * 1.3))
            self.assertEqual(journey['timing_summary']['bus_minutes'], 20)
            self.assertEqual(len(journey['legs'][1]['v1_signals']), 2)
            self.assertEqual(journey['crowding_summary']['status'], 'insufficient evidence')

    def test_same_stop_transfer_when_no_direct_bus(self):
        with tempfile.TemporaryDirectory() as tmp:
            planner = FallbackPlanner(network(Path(tmp)))
            result = planner.plan(28.600, 77.200, 28.627, 77.200, '2026-10-22T08:50:00+05:30')
            journey = result['journeys'][0]
            self.assertEqual([leg['route']['shortName'] for leg in journey['legs'] if leg['mode'] == 'BUS'], ['1UP', '2UP'])
            self.assertEqual(journey['numberOfTransfers'], 1)

    def test_missed_bus_and_far_points_return_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            planner = FallbackPlanner(network(Path(tmp)))
            self.assertEqual(planner.plan(28.600, 77.200, 28.618, 77.200, '2026-10-22T09:05:00+05:30')['journeys'], [])
            self.assertEqual(planner.plan(28.700, 77.300, 28.618, 77.200, '2026-10-22T08:50:00+05:30')['journeys'], [])
            with self.assertRaises(ValueError):
                planner.plan(28.600, 77.200, 28.618, 77.200, '2026-10-22T08:50:00')

    def test_api_falls_back_when_otp_missing_or_unrecorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            journeys = network(p)
            fallback = FallbackPlanner(journeys)
            params = parse_qs('from_lat=28.6&from_lon=77.2&to_lat=28.618&to_lon=77.2&departure=2026-10-22T08:50:00%2B05:30')
            result = mapped_journeys(params, p/'model.db', journeys, None, p, None, fallback)
            self.assertEqual(result['fallback_reason'], 'mapped routing is not configured')
            self.assertEqual(len(result['journeys']), 1)
            (p/'rec'/'otp').mkdir(parents=True)
            (p/'rec'/'manifest.json').write_text(json.dumps({'cases':[{'id':'x','from':[1,1],'to':[2,2],'departure':'2026-10-22T08:00:00+05:30'}]}))
            result = mapped_journeys(params, p/'model.db', journeys, None, p, RecordedOTP(p/'rec'), fallback)
            self.assertEqual(result['fallback_reason'], 'no recorded OTP response for this request')
            with self.assertRaises(ValueError):
                mapped_journeys(params, p/'model.db', None, None, p, None, None)

    def test_recorded_response_is_replayed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p/'otp').mkdir()
            (p/'manifest.json').write_text(json.dumps({'cases':[{'id':'case','origin':[28.6,77.2],'destination':[28.5,77.3],'departure':'2026-10-22T08:00:00+05:30'}]}))
            payload = {'data':{'planConnection':{'edges':[]}}}
            (p/'otp'/'case.json').write_text(json.dumps(payload))
            recorded = RecordedOTP(p)
            self.assertEqual(recorded(None, {'lat1':28.600001,'lon1':77.2,'lat2':28.5,'lon2':77.3,'when':'2026-10-22T08:00:00+05:30'}), payload)
            with self.assertRaises(LookupError):
                recorded(None, {'lat1':28.6,'lon1':77.2,'lat2':28.5,'lon2':77.3,'when':'2026-10-22T08:05:00+05:30'})


if __name__ == '__main__':
    unittest.main()
