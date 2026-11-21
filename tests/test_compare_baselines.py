import json
import sys
import tempfile
import unittest
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'src')); sys.path.insert(0,str(root/'scripts'))
from predict import create_database
from compare_baselines import compare

class ComparisonTests(unittest.TestCase):
    def test_common_target_coverage_and_time_separation(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            def data(start,end,n):
                return {'training_start':start,'training_end':end,'definition':'sample','quality':{},'records':[{'route':'8up','from_stop_id':'a','to_stop_id':'b','hour':9,'day_type':'weekday','date':start,'passengers':n}]}
            (p/'a.json').write_text(json.dumps(data('2026-10-01','2026-10-21',2)))
            (p/'b.json').write_text(json.dumps(data('2026-10-01','2026-10-21',4)))
            (p/'val.json').write_text(json.dumps(data('2026-10-22','2026-10-24',3)))
            create_database(p/'a.json',p/'a.db'); create_database(p/'b.json',p/'b.db')
            result=compare(p/'a.db',p/'b.db',p/'val.json')
            self.assertEqual(result['common_predictions'],1)
            self.assertEqual(result['v1_mean_absolute_error_on_common'],1)
            self.assertEqual(result['v2_mean_absolute_error_on_common'],1)
            with self.assertRaises(ValueError): compare(p/'a.db',p/'b.db',p/'a.json')

if __name__=='__main__':unittest.main()
