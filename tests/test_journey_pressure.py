import sqlite3
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from journey_pressure import pressure, estimate, compare


class JourneyPressureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.temp.name) / 'model.db')
        with sqlite3.connect(self.db) as db:
            db.execute('CREATE TABLE scheduled_totals(route,origin,destination,hour,day_type,scheduled_crossings)')
            db.execute('CREATE TABLE service_signals(route,origin,destination,hour,day_type,sampled_passengers)')
            db.executemany('INSERT INTO scheduled_totals VALUES (?,?,?,?,?,?)', [('r','A','B',8,'weekday',10),('r','B','C',8,'weekday',10)])
            db.execute('INSERT INTO service_signals VALUES (?,?,?,?,?,?)', ('r','A','B',8,'weekday',1))

    def tearDown(self):
        self.temp.cleanup()

    def test_one_ticket_and_route_fallback_use_scheduled_denominator(self):
        self.assertAlmostEqual(pressure(self.db,'r','A','B','weekday',8)['score'], .1)
        fallback = pressure(self.db,'r','B','C','weekday',8)
        self.assertEqual(fallback['tier'], 'route_window')
        self.assertAlmostEqual(fallback['score'], .05)

    def test_unknown_route_remains_unavailable(self):
        self.assertIsNone(pressure(self.db,'UNKNOWN','A','B','weekday',8))

    def test_cross_day_fallback_is_explicit(self):
        result = pressure(self.db,'r','A','B','sunday',18)
        self.assertEqual(result['tier'], 'route_all_days')
        self.assertAlmostEqual(result['score'], .05)

    def test_leg_weighted_and_relative_ties(self):
        def leg(route, duration, origin='A', dest='B'):
            return {'mode':'BUS','route':{'shortName':route},'duration_minutes':duration,
                    'start':{'scheduledTime':'2026-11-02T08:00:00+05:30'},
                    'v1_signals':[{'from_stop_id':origin,'to_stop_id':dest}]}
        j = {'legs':[leg('R', 10),leg('R', 30, 'B','C')]}
        self.assertAlmostEqual(estimate(j,self.db)['score'], .0625)
        js = [j, {'legs':[leg('R', 10)]}]
        compare(js,[0,1],self.db)
        self.assertEqual(js[0]['journey_pressure']['label'], 'Low estimated crowding')
        self.assertEqual(js[1]['journey_pressure']['label'], 'Low estimated crowding')
        one = [{'legs':[leg('R', 10)]}]
        compare(one,[0],self.db)
        self.assertEqual(one[0]['journey_pressure']['label'], js[1]['journey_pressure']['label'])
        self.assertEqual(estimate({'legs':[leg('R',10),leg('NONE',10)]}, self.db)['status'],'unavailable')


if __name__ == '__main__':
    unittest.main()
