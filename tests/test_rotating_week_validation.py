import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from rotating_week_validation import evaluate

class RotatingWeekTests(unittest.TestCase):
    def test_rejects_data_declaring_final_week(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'records.json'
            p.write_text(json.dumps({'training_start':'2026-10-01','training_end':'2026-10-31','records':[]}))
            with self.assertRaises(ValueError): evaluate(p, tmp)

    def test_rejects_out_of_period_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'records.json'
            p.write_text(json.dumps({'training_start':'2026-10-01','training_end':'2026-10-21','records':[{'date':'2026-10-25','day_type':'sunday'}]}))
            with self.assertRaises(ValueError): evaluate(p, tmp)

    def test_zero_evidence_does_not_create_supported_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'records.json'
            p.write_text(json.dumps({'training_start':'2026-10-01','training_end':'2026-10-21','records':[]}))
            with patch('rotating_week_validation.scheduled_crossings',return_value={}):
                result=evaluate(p,tmp)
            self.assertEqual(len(result['folds']),3)
            self.assertTrue(all(x['decisive_pair_concordance'] is None for x in result['folds']))

if __name__=='__main__': unittest.main()
