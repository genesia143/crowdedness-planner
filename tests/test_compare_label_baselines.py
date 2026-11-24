import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'src')); sys.path.insert(0, str(root / 'scripts'))
from compare_label_baselines import evaluate
from predict import create_database
import validate_v1_labels

DEFINITION = 'observed ticket-sample passenger journeys crossing a segment, grouped by ticket boarding hour'


def write(path, fields, values):
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(values)


class BaselineComparisonTests(unittest.TestCase):
    def build(self, p):
        """One route a-b-c with a bus at 07, 08 and 09; segment a-b is busiest at 09, b-c at 07."""
        write(p/'routes.txt', ['route_id', 'route_short_name'], [{'route_id': 'r', 'route_short_name': '8UP'}])
        write(p/'trips.txt', ['trip_id', 'route_id', 'service_id'], [{'trip_id': f't{h}', 'route_id': 'r', 'service_id': 's'} for h in (7, 8, 9)])
        write(p/'stop_times.txt', ['trip_id', 'stop_id', 'stop_sequence', 'departure_time'],
              [{'trip_id': f't{h}', 'stop_id': s, 'stop_sequence': i, 'departure_time': f'{h:02d}:{10 * i:02d}:00'} for h in (7, 8, 9) for i, s in enumerate('abc')])
        write(p/'calendar.txt', ['service_id', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'start_date', 'end_date'],
              [{'service_id': 's', 'monday': 1, 'tuesday': 1, 'wednesday': 1, 'thursday': 1, 'friday': 1, 'saturday': 0, 'sunday': 0, 'start_date': '20261001', 'end_date': '20261031'}])
        pattern = {('a', 'b'): {7: 4, 8: 8, 9: 12}, ('b', 'c'): {7: 12, 8: 8, 9: 4}}
        def records(days):
            return [{'route': '8up', 'from_stop_id': a, 'to_stop_id': b, 'date': day, 'hour': h, 'day_type': 'weekday', 'passengers': n}
                    for day in days for (a, b), hours in pattern.items() for h, n in hours.items()]
        (p/'train.json').write_text(json.dumps({'training_start': '2026-10-05', 'training_end': '2026-10-09', 'definition': DEFINITION, 'quality': {},
                                                 'records': records(['2026-10-05', '2026-10-06', '2026-10-07'])}))
        create_database(p/'train.json', p/'model.db', gtfs=p)
        (p/'tune.json').write_text(json.dumps({'training_start': '2026-10-22', 'training_end': '2026-10-23', 'definition': DEFINITION, 'quality': {},
                                                'records': records(['2026-10-22', '2026-10-23'])}))

    def test_model_matches_existing_validator_and_baselines_are_scored_on_same_hours(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp); self.build(p)
            result = evaluate(p/'model.db', p/'tune.json', p)['by_day_type']['weekday']
            existing = validate_v1_labels.evaluate(p/'model.db', p/'tune.json', p)['by_day_type']['weekday']
            self.assertEqual(result['evaluated_hours'], existing['evaluated_hours'])
            self.assertAlmostEqual(result['model']['agreement'], existing['agreement_rate'])
            self.assertEqual(result['model']['agreement'], 1.0)
            # The two stretches peak at opposite ends, so a single route or citywide pattern cannot fit both.
            self.assertLess(result['route']['agreement'], 1.0)
            self.assertLess(result['citywide']['agreement'], 1.0)
            self.assertAlmostEqual(result['always_typical']['agreement'], 2 / 6)

    def test_refuses_dates_outside_tuning_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp); self.build(p)
            data = json.loads((p/'tune.json').read_text()); data['training_end'] = '2026-10-25'
            (p/'tune.json').write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                evaluate(p/'model.db', p/'tune.json', p)


if __name__ == '__main__':
    unittest.main()
