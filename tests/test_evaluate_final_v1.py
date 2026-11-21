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
                    CREATE TABLE service_signals(route,origin,destination,hour,day_type,sampled_passengers,matched_days);
                    CREATE TABLE sunday_observation_days(route,origin,destination,hour,day_type,day_mask);''')
                db.executemany('INSERT INTO metadata VALUES (?,?)', [('training_start', '"2026-10-01"'), ('training_end', '"2026-10-21"'), ('definition', '"grouped by ticket boarding hour"'), ('day_type_scheme', '"weekday_saturday_sunday_v1"')])
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
                db.executescript('CREATE TABLE metadata(key,value); CREATE TABLE scheduled_totals(route,origin,destination,hour,day_type,scheduled_crossings,scheduled_days); CREATE TABLE service_signals(route,origin,destination,hour,day_type,sampled_passengers,matched_days); CREATE TABLE sunday_observation_days(route,origin,destination,hour,day_type,day_mask);')
                db.executemany('INSERT INTO metadata VALUES (?,?)', [('training_start','"2026-10-01"'), ('training_end','"2026-10-21"'), ('definition','"grouped by ticket boarding hour"'), ('day_type_scheme','"weekday_saturday_sunday_v1"')])
                for hour, passengers in [(8,10),(9,20),(10,30)]:
                    db.execute('INSERT INTO scheduled_totals VALUES (?,?,?,?,?,?,?)',('R','A','B',hour,'weekday',2,4))
                    db.execute('INSERT INTO service_signals VALUES (?,?,?,?,?,?,?)',('R','A','B',hour,'weekday',passengers,3))
                db.execute('INSERT INTO scheduled_totals VALUES (?,?,?,?,?,?,?)',('R','A','B',11,'weekday',2,4))
            records=[{'route':'R','from_stop_id':'A','to_stop_id':'B','date':'2026-10-26','hour':hour,'day_type':'weekday','passengers':count} for hour,count in [(8,3),(11,1),(12,2)]]
            path=root/'holdout.json';path.write_text(json.dumps({'training_start':final.START,'training_end':final.END,'definition':'grouped by ticket boarding hour','quality':{},'records':records}))
            schedule={('R','A','B','2026-10-26',h,'weekday'):2 for h in [8,9,10,11]}
            with patch.object(final,'scheduled_crossings',return_value=schedule): result=final.evaluate(dbfile,path,root)
            self.assertEqual(result['subgroups']['weekday']['labelled_sample_passenger_segment_coverage'],0.75)
            self.assertEqual(result['subgroups']['weekday']['unscheduled_sample_passenger_segments'],2)
            self.assertEqual(result['subgroups']['weekday']['all_matched_sample_passenger_segments'],6)
            self.assertEqual(result['subgroups']['weekday']['labelled_all_matched_sample_passenger_segment_coverage'],0.5)

    def test_cli_refuses_changed_target_before_writing_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); output = root / 'report.json'
            args = ['eval', '--database','db', '--validation','target', '--gtfs','gtfs', '--mapping','map', '--training-records','training', '--source','src', '--manifest','manifest', '--output',str(output), '--confirm-final-evaluation']
            with patch.object(sys, 'argv', args), patch.object(final, 'checked_source', return_value='src'), patch.object(final, 'verify', return_value=True), patch.object(final, 'fingerprint', side_effect=[{'sha256':'first'}, {'sha256':'changed'}]), patch.object(final, 'evaluate', return_value={}):
                with self.assertRaisesRegex(ValueError, 'target changed'):
                    final.main()
            self.assertFalse(output.exists())

    def test_calendar_groups(self):
        self.assertEqual(final.subgroup('2026-10-25'), 'sunday')
        self.assertEqual(final.subgroup('2026-10-31'), 'saturday')

    def test_evaluator_uses_production_labels_and_reports_evidence_tiers(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); dbfile = root / 'model.db'
            with sqlite3.connect(dbfile) as db:
                db.executescript('CREATE TABLE metadata(key,value); CREATE TABLE scheduled_totals(route,origin,destination,hour,day_type,scheduled_crossings,scheduled_days); CREATE TABLE service_signals(route,origin,destination,hour,day_type,sampled_passengers,matched_days); CREATE TABLE sunday_observation_days(route,origin,destination,hour,day_type,day_mask);')
                db.executemany('INSERT INTO metadata VALUES (?,?)', [('training_start','"2026-10-01"'), ('training_end','"2026-10-21"'), ('definition','"grouped by ticket boarding hour"'), ('day_type_scheme','"weekday_saturday_sunday_v1"')])
                for hour in range(8,12):
                    db.execute('INSERT INTO scheduled_totals VALUES (?,?,?,?,?,?,?)', ('R','A','B',hour,'sunday',3,3))
            records = [{'route':'R','from_stop_id':'A','to_stop_id':'B','date':'2026-10-25','hour':h,'day_type':'sunday','passengers':h-7} for h in range(8,12)]
            path = root / 'synthetic.json'
            path.write_text(json.dumps({'training_start':final.START,'training_end':final.END,'definition':'grouped by ticket boarding hour','quality':{},'records':records}))
            schedule = {('R','A','B','2026-10-25',h,'sunday'):1 for h in range(8,12)}
            bands = {8:{'label':'likely quieter','relative_percentile':0.1}, 9:{'label':'typical','relative_percentile':0.5,'evidence_tier':'broader_window'}, 10:{'label':'likely busier','relative_percentile':0.9,'evidence_tier':'broader_window'}, 11:{'label':'insufficient evidence'}}
            with patch.object(final, 'scheduled_crossings', return_value=schedule), patch.object(final, 'relative_band', side_effect=lambda db,r,a,b,k,h: bands[h]):
                sunday = final.evaluate(dbfile,path,root)['subgroups']['sunday']
            self.assertEqual(sunday['labelled_sample_passenger_segments'], 6)
            self.assertEqual(sunday['strict_labelled_sample_passenger_segments'], 1)
            self.assertEqual(sunday['broader_window_labelled_sample_passenger_segments'], 5)
            self.assertEqual(sunday['unlabelled_scheduled_cells'], 1)
            self.assertEqual(sunday['rankings']['mixed_tier_groups_excluded'], 1)
            self.assertEqual(sunday['label_agreement']['broader_window_evaluated_hours'], 2)

    def test_label_agreement_by_actual_day_and_insufficient_target(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dbfile = root / 'model.db'
            with sqlite3.connect(dbfile) as db:
                db.executescript('CREATE TABLE metadata(key,value); CREATE TABLE scheduled_totals(route,origin,destination,hour,day_type,scheduled_crossings,scheduled_days); CREATE TABLE service_signals(route,origin,destination,hour,day_type,sampled_passengers,matched_days); CREATE TABLE sunday_observation_days(route,origin,destination,hour,day_type,day_mask);')
                db.executemany('INSERT INTO metadata VALUES (?,?)', [('training_start','"2026-10-01"'), ('training_end','"2026-10-21"'), ('definition','"grouped by ticket boarding hour"'), ('day_type_scheme','"weekday_saturday_sunday_v1"')])
                for kind in ('weekday', 'saturday', 'sunday'):
                    for hour, passengers in [(8,10),(9,20),(10,30)]:
                        db.execute('INSERT INTO scheduled_totals VALUES (?,?,?,?,?,?,?)', ('R','A','B',hour,kind,2,4))
                        db.execute('INSERT INTO service_signals VALUES (?,?,?,?,?,?,?)', ('R','A','B',hour,kind,passengers,3))
            schedule = {}
            records = []
            # Weekday target reverses the training order; Saturday target ties,
            # so its three hours are ineligible for target rank comparison.
            for day, kind, values in [('2026-10-26','weekday',[3,2,1]), ('2026-10-31','saturday',[1,1,1])]:
                for hour, count in zip((8,9,10), values):
                    schedule[('R','A','B',day,hour,kind)] = 1
                    records.append({'route':'R','from_stop_id':'A','to_stop_id':'B','date':day,'hour':hour,'day_type':kind,'passengers':count})
            path = root / 'synthetic.json'
            path.write_text(json.dumps({'training_start':final.START,'training_end':final.END,'definition':'grouped by ticket boarding hour','quality':{},'records':records}))
            with patch.object(final, 'scheduled_crossings', return_value=schedule):
                result = final.evaluate(dbfile, path, root)['subgroups']
            weekday = result['weekday']['label_agreement']
            self.assertEqual(weekday['evaluated_hours'], 3)
            self.assertAlmostEqual(weekday['agreement_rate'], 1/3)
            self.assertEqual(weekday['prediction=likely quieter|target=likely busier'], 1)
            self.assertEqual(result['saturday']['label_agreement']['common_hours_excluded_no_target_rank'], 3)
            self.assertIsNone(result['sunday']['label_agreement']['agreement_rate'])


if __name__ == '__main__':
    unittest.main()
