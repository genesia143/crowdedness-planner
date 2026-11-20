import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from predict import create_database, query

class PredictionTests(unittest.TestCase):
    def test_observed_day_mean_and_missing_signal(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            data = {'training_start':'2026-10-01', 'training_end':'2026-10-21', 'definition':'sample', 'quality':{}, 'records':[
                {'route':'8up','from_stop_id':'a','to_stop_id':'b','hour':9,'day_type':'weekday','date':'2026-10-01','passengers':2},
                {'route':'8up','from_stop_id':'a','to_stop_id':'b','hour':9,'day_type':'weekday','date':'2026-10-02','passengers':6}]}
            (p/'source.json').write_text(json.dumps(data))
            create_database(p/'source.json', p/'model.db')
            result = query(p/'model.db','8UP','a','b','2026-10-05T09:00:00+05:30')
            self.assertEqual(result['sample_passengers_per_observed_day'], 4)
            self.assertEqual(result['observed_days'], 2)
            self.assertEqual(query(p/'model.db','8UP','a','b','2026-10-04T09:00:00+05:30')['status'], 'unavailable')
            with self.assertRaises(ValueError):
                query(p/'model.db','8UP','a','b','2026-10-05T09:00:00')

if __name__ == '__main__':
    unittest.main()
