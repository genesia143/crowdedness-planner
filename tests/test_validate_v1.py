import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('validate_v1', Path(__file__).resolve().parents[1] / 'scripts' / 'validate_v1.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ValidateV1Test(unittest.TestCase):
    def test_zero_sample_day_and_schedule_coverage(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            database = base / 'model.db'
            with sqlite3.connect(database) as db:
                db.execute('CREATE TABLE metadata (key TEXT, value TEXT)')
                db.executemany('INSERT INTO metadata VALUES (?,?)', [(k, json.dumps(v)) for k, v in {'training_start':'2026-10-01', 'training_end':'2026-10-21'}.items()])
                db.execute('CREATE TABLE scheduled_totals (route TEXT,origin TEXT,destination TEXT,hour INTEGER,day_type TEXT,scheduled_crossings INTEGER)')
                db.execute('CREATE TABLE service_signals (route TEXT,origin TEXT,destination TEXT,hour INTEGER,day_type TEXT,sampled_passengers INTEGER)')
                db.execute("INSERT INTO scheduled_totals VALUES ('r','a','b',8,'weekday',10)")
                db.execute("INSERT INTO service_signals VALUES ('r','a','b',8,'weekday',20)")
            validation = base / 'validation.json'
            validation.write_text(json.dumps({'training_start':'2026-10-22', 'training_end':'2026-10-23', 'quality':{}, 'records':[{'route':'r','from_stop_id':'a','to_stop_id':'b','date':'2026-10-22','hour':8,'day_type':'weekday','passengers':2}]}))
            schedule = {('r','a','b','2026-10-22',8,'weekday'): 2, ('r','a','b','2026-10-23',8,'weekday'): 2}
            with patch.object(module, 'scheduled_crossings', return_value=schedule):
                report = module.evaluate(database, validation, base)
            row = report['day_types']['weekday']
            self.assertEqual(row['scheduled_cells'], 2)
            self.assertEqual(row['matched_cells'], 1)
            self.assertEqual(row['mean_absolute_error_per_crossing'], 1.5)

    def test_reserved_week_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'validation.json'
            path.write_text(json.dumps({'training_start':'2026-10-25','training_end':'2026-10-31'}))
            with self.assertRaises(ValueError):
                module.evaluate(Path(temp) / 'missing.db', path, temp)


if __name__ == '__main__':
    unittest.main()
