import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from holiday_magnitude_study import check_records, remove_holidays

class HolidayStudyTest(unittest.TestCase):
    def test_remove_numerator_and_denominator_together(self):
        self.assertEqual(remove_holidays(30, 10, 6, 2), 3)
        self.assertIsNone(remove_holidays(30, 2, 6, 2))
        self.assertIsNone(remove_holidays(5, 10, 6, 2))

    def test_reject_holdout_or_wrong_day(self):
        record={'date':'2026-10-25','day_type':'sunday'}
        data={'training_start':'2026-10-01','training_end':'2026-10-21','records':[record]}
        with self.assertRaises(ValueError): check_records(data, '2026-10-01','2026-10-21')
        record.update(date='2026-10-20',day_type='sunday')
        with self.assertRaises(ValueError): check_records(data, '2026-10-01','2026-10-21')
