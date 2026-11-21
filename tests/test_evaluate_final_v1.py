import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
spec = importlib.util.spec_from_file_location('evaluate_final_v1', Path(__file__).resolve().parents[1] / 'scripts/evaluate_final_v1.py')
final = importlib.util.module_from_spec(spec)
spec.loader.exec_module(final)


class FinalEvaluationTests(unittest.TestCase):
    def test_source_must_be_actual_imported_checkout(self):
        self.assertEqual(final.checked_source(final.SOURCE_DIR), str(final.SOURCE_DIR))
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                final.checked_source(temp)

    def test_synthetic_zero_inclusion_and_subgroups(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dbfile = root / 'model.db'
            with sqlite3.connect(dbfile) as db:
                db.executescript('''CREATE TABLE metadata(key, value);
                    CREATE TABLE scheduled_totals(route,origin,destination,hour,day_type,scheduled_crossings,scheduled_days);
                    CREATE TABLE service_signals(route,origin,destination,hour,day_type,sampled_passengers,matched_days);''')
                db.executemany('INSERT INTO metadata VALUES (?,?)', [('training_start', '"2026-10-01"'), ('training_end', '"2026-10-21"'), ('definition', '"grouped by ticket boarding hour"')])
                db.execute('INSERT INTO scheduled_totals VALUES (?,?,?,?,?,?,?)', ('R', 'A', 'B', 8, 'weekday', 2, 4))
                db.execute('INSERT INTO service_signals VALUES (?,?,?,?,?,?,?)', ('R', 'A', 'B', 8, 'weekday', 10, 3))
            data = root / 'holdout.json'
            data.write_text(json.dumps({'training_start': final.START, 'training_end': final.END, 'definition': 'grouped by ticket boarding hour', 'quality': {}, 'records': []}))
            schedule = {('R', 'A', 'B', '2026-10-26', 8, 'weekday'): 2}
            with patch.object(final, 'scheduled_crossings', return_value=schedule):
                result = final.evaluate(dbfile, data, root)
            self.assertEqual(result['subgroups']['weekday']['mean_absolute_error_per_crossing'], 5)
            self.assertEqual(result['subgroups']['weekday']['matched_cells'], 0)
            self.assertIsNone(result['subgroups']['sunday']['mean_absolute_error_per_crossing'])
            data.write_text(json.dumps({'training_start': '2026-10-24', 'training_end': final.END, 'quality': {}, 'records': []}))
            with self.assertRaises(ValueError):
                final.evaluate(dbfile, data, root)

    def test_label_coverage_uses_provisional_support_rules(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); dbfile = root / 'model.db'
            with sqlite3.connect(dbfile) as db:
                db.executescript('CREATE TABLE metadata(key,value); CREATE TABLE scheduled_totals(route,origin,destination,hour,day_type,scheduled_crossings,scheduled_days); CREATE TABLE service_signals(route,origin,destination,hour,day_type,sampled_passengers,matched_days);')
                db.executemany('INSERT INTO metadata VALUES (?,?)', [('training_start','"2026-10-01"'), ('training_end','"2026-10-21"'), ('definition','"grouped by ticket boarding hour"')])
                for hour, passengers in [(8,10),(9,20),(10,30)]:
                    db.execute('INSERT INTO scheduled_totals VALUES (?,?,?,?,?,?,?)',('R','A','B',hour,'weekday',2,4))
                    db.execute('INSERT INTO service_signals VALUES (?,?,?,?,?,?,?)',('R','A','B',hour,'weekday',passengers,3))
                db.execute('INSERT INTO scheduled_totals VALUES (?,?,?,?,?,?,?)',('R','A','B',11,'weekday',2,4))
            records=[{'route':'R','from_stop_id':'A','to_stop_id':'B','date':'2026-10-26','hour':hour,'day_type':'weekday','passengers':count} for hour,count in [(8,3),(11,1)]]
            path=root/'holdout.json';path.write_text(json.dumps({'training_start':final.START,'training_end':final.END,'definition':'grouped by ticket boarding hour','quality':{},'records':records}))
            schedule={('R','A','B','2026-10-26',h,'weekday'):2 for h in [8,9,10,11]}
            with patch.object(final,'scheduled_crossings',return_value=schedule): result=final.evaluate(dbfile,path,root)
            self.assertEqual(result['subgroups']['weekday']['labelled_sample_passenger_segment_coverage'],0.75)

    def test_calendar_groups(self):
        self.assertEqual(final.subgroup('2026-10-25'), 'sunday')
        self.assertEqual(final.subgroup('2026-10-31'), 'saturday')


if __name__ == '__main__':
    unittest.main()
