import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from operator_view import busiest, route_names
from predict import create_database

DEFINITION = 'observed ticket-sample passenger journeys crossing a segment, grouped by ticket boarding hour'


def write(path, fields, values):
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(values)


class OperatorViewTests(unittest.TestCase):
    def build(self, p):
        write(p/'routes.txt', ['route_id', 'route_short_name'], [{'route_id': 'r', 'route_short_name': '8UP'}])
        write(p/'trips.txt', ['trip_id', 'route_id', 'service_id'], [{'trip_id': 't', 'route_id': 'r', 'service_id': 's'}])
        write(p/'stop_times.txt', ['trip_id', 'stop_id', 'stop_sequence', 'departure_time'],
              [{'trip_id': 't', 'stop_id': s, 'stop_sequence': i, 'departure_time': time} for i, (s, time) in enumerate([('a', '09:00:00'), ('b', '09:10:00'), ('c', '09:20:00')])])
        write(p/'calendar.txt', ['service_id', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'start_date', 'end_date'],
              [{'service_id': 's', 'monday': 1, 'tuesday': 1, 'wednesday': 1, 'thursday': 1, 'friday': 1, 'saturday': 0, 'sunday': 0, 'start_date': '20261001', 'end_date': '20261031'}])
        records = [{'route': '8up', 'from_stop_id': 'a', 'to_stop_id': 'b', 'date': '2026-10-05', 'hour': 9, 'day_type': 'weekday', 'passengers': 30},
                   {'route': '8up', 'from_stop_id': 'b', 'to_stop_id': 'c', 'date': '2026-10-05', 'hour': 9, 'day_type': 'weekday', 'passengers': 12}]
        (p/'data.json').write_text(json.dumps({'training_start': '2026-10-05', 'training_end': '2026-10-09', 'definition': DEFINITION, 'quality': {}, 'records': records}))
        create_database(p/'data.json', p/'model.db', gtfs=p)

    def test_ranks_by_passengers_per_scheduled_crossing_with_evidence_floor(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp); self.build(p)
            stops, coords = {'a': 'Alpha', 'b': 'Beta', 'c': 'Gamma'}, {'a': (28.6, 77.2), 'b': (28.61, 77.2)}
            result = busiest(p/'model.db', stops, coords, route_names(p), 'weekday', 8, 10, 10, 10)
            self.assertEqual([(s['route'], s['from']['name'], s['to']['name']) for s in result['stretches']], [('8UP', 'Alpha', 'Beta'), ('8UP', 'Beta', 'Gamma')])
            # Five scheduled weekdays with one crossing each; zero-ticket days stay in the denominator.
            self.assertEqual(result['stretches'][0]['scheduled_crossings'], 5)
            self.assertAlmostEqual(result['stretches'][0]['pressure'], 6.0)
            self.assertIsNone(result['stretches'][1]['to']['lat'])
            self.assertEqual(result['routes'][0]['sample_passengers'], 42)
            filtered = busiest(p/'model.db', stops, coords, {}, 'weekday', 8, 10, 10, 20)
            self.assertEqual(filtered['qualifying_stretches'], 1)
            self.assertEqual(busiest(p/'model.db', stops, coords, {}, 'saturday', 8, 10, 10, 1)['stretches'], [])

    def test_rejects_invalid_filters(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp); self.build(p)
            for args in [('holiday', 8, 9, 10, 10), ('weekday', 9, 8, 10, 10), ('weekday', 8, 9, 0, 10), ('weekday', 'x', 9, 10, 10)]:
                with self.subTest(args=args), self.assertRaises(ValueError):
                    busiest(p/'model.db', {}, {}, {}, *args)


if __name__ == '__main__':
    unittest.main()
