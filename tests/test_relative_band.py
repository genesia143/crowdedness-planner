import sqlite3
import unittest
from pathlib import Path
import sys
import json
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from predict import relative_band, create_database


class RelativeBandTest(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.addCleanup(self.db.close)
        self.db.execute('CREATE TABLE service_signals (route TEXT, origin TEXT, destination TEXT, hour INTEGER, day_type TEXT, matched_days INTEGER, sampled_passengers INTEGER, scheduled_crossings INTEGER, unmatched_days INTEGER)')
        self.db.execute('CREATE TABLE scheduled_totals (route TEXT, origin TEXT, destination TEXT, hour INTEGER, day_type TEXT, scheduled_days INTEGER, scheduled_crossings INTEGER)')

    def add(self, hour, passengers, days=3, route='8UP', scheduled_days=4, crossings=10):
        self.db.execute('INSERT INTO service_signals VALUES (?,?,?,?,?,?,?,?,?)',
                        (route, 'a', 'b', hour, 'weekday', days, passengers, crossings, 0))
        self.db.execute('INSERT INTO scheduled_totals VALUES (?,?,?,?,?,?,?)',
                        (route, 'a', 'b', hour, 'weekday', scheduled_days, crossings))

    def band(self, hour):
        return relative_band(self.db, '8UP', 'a', 'b', 'weekday', hour)

    def test_ranks_use_same_segment_and_all_scheduled_crossings(self):
        self.add(8, 10)
        self.add(9, 20)
        self.add(10, 30)
        self.add(9, 1000, route='OTHER')
        self.assertEqual([self.band(h)['label'] for h in (8, 9, 10)],
                         ['likely quieter', 'typical', 'likely busier'])
        self.assertTrue(self.band(9)['provisional'])
        self.assertEqual(self.band(9)['reference_hours'], 3)

    def test_sparse_or_identical_data_is_not_given_a_band(self):
        self.add(8, 10)
        self.add(9, 10)
        self.add(10, 10)
        self.assertEqual(self.band(8)['label'], 'insufficient evidence')
        self.add(11, 20, days=2)
        self.assertEqual(self.band(11)['label'], 'insufficient evidence')
        self.assertEqual(self.band(12)['label'], 'insufficient evidence')

    def test_saturday_and_sunday_require_all_three_training_days(self):
        for kind in ('saturday', 'sunday'):
            for hour, passengers in [(8,10),(9,20),(10,30)]:
                self.db.execute('INSERT INTO service_signals VALUES (?,?,?,?,?,?,?,?,?)',('8UP','a','b',hour,kind,3,passengers,3,0))
                self.db.execute('INSERT INTO scheduled_totals VALUES (?,?,?,?,?,?,?)',('8UP','a','b',hour,kind,3,3))
            self.assertEqual(relative_band(self.db,'8UP','a','b',kind,8)['label'],'likely quieter')
            self.db.execute('UPDATE service_signals SET matched_days=2 WHERE route=? AND day_type=? AND hour=?',('8UP',kind,8))
            self.assertEqual(relative_band(self.db,'8UP','a','b',kind,8)['label'],'insufficient evidence')

    def test_ties_share_midrank(self):
        self.add(8, 10)
        self.add(9, 10)
        self.add(10, 30)
        self.assertEqual(self.band(8)['relative_percentile'], self.band(9)['relative_percentile'])

    def test_sunday_fallback_pools_distinct_days_and_prefers_strict_band(self):
        self.db.execute('CREATE TABLE sunday_observation_days (route TEXT, origin TEXT, destination TEXT, hour INTEGER, day_type TEXT, day_mask INTEGER)')
        for hour, passengers, mask in [(7, 2, 1), (8, 4, 2), (9, 6, 1), (10, 10, 2), (11, 20, 1)]:
            self.db.execute('INSERT INTO service_signals VALUES (?,?,?,?,?,?,?,?,?)', ('8UP','a','b',hour,'sunday',1,passengers,3,0))
            self.db.execute('INSERT INTO scheduled_totals VALUES (?,?,?,?,?,?,?)', ('8UP','a','b',hour,'sunday',3,3))
            self.db.execute('INSERT INTO sunday_observation_days VALUES (?,?,?,?,?,?)', ('8UP','a','b',hour,'sunday',mask))
        result = relative_band(self.db,'8UP','a','b','sunday',8)
        self.assertEqual(result['evidence_tier'], 'broader_window')
        self.assertEqual(result['matched_days_in_window'], 2)
        self.assertEqual(result['sample_passengers_in_window'], 12)
        self.assertEqual(result['scheduled_crossings_in_window'], 9)
        self.assertIn('not actual crowding', result['limitation'])
        self.db.execute("UPDATE service_signals SET matched_days=3,sampled_passengers=hour*2 WHERE day_type='sunday'")
        strict = relative_band(self.db,'8UP','a','b','sunday',8)
        self.assertNotIn('evidence_tier', strict)
        self.assertEqual(strict['reference_hours'], 5)

    def test_sunday_window_does_not_count_same_observed_day_twice(self):
        self.db.execute('CREATE TABLE sunday_observation_days (route TEXT, origin TEXT, destination TEXT, hour INTEGER, day_type TEXT, day_mask INTEGER)')
        for hour in range(7, 12):
            self.db.execute('INSERT INTO service_signals VALUES (?,?,?,?,?,?,?,?,?)', ('8UP','a','b',hour,'sunday',1,10,3,0))
            self.db.execute('INSERT INTO scheduled_totals VALUES (?,?,?,?,?,?,?)', ('8UP','a','b',hour,'sunday',3,3))
            self.db.execute('INSERT INTO sunday_observation_days VALUES (?,?,?,?,?,?)', ('8UP','a','b',hour,'sunday',1))
        self.assertEqual(relative_band(self.db,'8UP','a','b','sunday',8)['label'], 'insufficient evidence')

    def test_old_index_explicitly_requests_rebuild_for_sunday_fallback(self):
        result = relative_band(self.db,'8UP','a','b','sunday',8)
        self.assertIn('rebuilt model index', result['reason'])

    def test_index_records_distinct_sunday_dates_only_for_scheduled_records(self):
        records = [{'route':'8UP', 'from_stop_id':'a', 'to_stop_id':'b', 'hour':8,
                    'day_type':'sunday', 'date':day, 'passengers':2}
                   for day in ('2026-10-04', '2026-10-11', '2026-10-18')]
        data = {'training_start':'2026-10-01', 'training_end':'2026-10-21',
                'definition':'test', 'quality':{}, 'records':records}
        schedule = {('8UP','a','b',day,8,'sunday'):1 for day in ('2026-10-04','2026-10-11')}
        with tempfile.TemporaryDirectory() as temp:
            source, destination = Path(temp)/'records.json', Path(temp)/'model.db'
            source.write_text(json.dumps(data), encoding='utf-8')
            with patch('service.scheduled_crossings', return_value=schedule):
                create_database(source, destination, 'dummy')
            with sqlite3.connect(destination) as db:
                mask = db.execute('SELECT day_mask FROM sunday_observation_days').fetchone()[0]
                self.assertEqual(mask, (1 << 3) | (1 << 10))


if __name__ == '__main__':
    unittest.main()
