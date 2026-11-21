import sqlite3
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from predict import relative_band


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


if __name__ == '__main__':
    unittest.main()
