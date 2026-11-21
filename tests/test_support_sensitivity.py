import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / 'scripts' / 'sensitivity_support.py'
spec = importlib.util.spec_from_file_location('sensitivity_support', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SupportSensitivityTest(unittest.TestCase):
    def test_threshold_tradeoff_and_tuning_period_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            dbpath = Path(directory) / 'model.db'
            validation = Path(directory) / 'validation.json'
            with sqlite3.connect(dbpath) as db:
                db.execute('CREATE TABLE metadata (key TEXT, value TEXT)')
                db.execute('INSERT INTO metadata VALUES (?,?)', ('training_end', json.dumps('2026-10-21')))
                db.execute('CREATE TABLE service_signals (route TEXT,origin TEXT,destination TEXT,day_type TEXT,hour INTEGER,matched_days INTEGER,sampled_passengers INTEGER)')
                db.execute('CREATE TABLE scheduled_totals (route TEXT,origin TEXT,destination TEXT,day_type TEXT,hour INTEGER,scheduled_days INTEGER,scheduled_crossings INTEGER)')
                for hour, days, passengers in [(8,3,10),(9,3,20),(10,2,5)]:
                    db.execute('INSERT INTO service_signals VALUES (?,?,?,?,?,?,?)', ('R','A','B','weekday',hour,days,passengers))
                    db.execute('INSERT INTO scheduled_totals VALUES (?,?,?,?,?,?,?)', ('R','A','B','weekday',hour,4,10))
            data = {'training_start':'2026-10-22','training_end':'2026-10-22', 'records': [
                {'route':'R','from_stop_id':'A','to_stop_id':'B','date':'2026-10-22','hour':h,'day_type':'weekday','passengers':n}
                for h,n in [(8,1),(9,2),(10,3)]]}
            validation.write_text(json.dumps(data))
            schedule = {('R','A','B','2026-10-22',h,'weekday'):1 for h in (8,9,10)}
            with patch.object(module, 'scheduled_crossings', return_value=schedule):
                result = module.evaluate(dbpath,validation,'unused',[(3,10,4),(2,5,4)])
            self.assertEqual(result['variants'][0]['covered_sample_passenger_segments'],0)
            self.assertEqual(result['variants'][1]['covered_sample_passenger_segments'],6)
            self.assertEqual(result['variants'][1]['rankings']['weekday']['concordant'],1)
            data['training_end'] = '2026-10-25'
            validation.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                module.evaluate(dbpath,validation,'unused',[(2,5,4)])

if __name__ == '__main__':
    unittest.main()
