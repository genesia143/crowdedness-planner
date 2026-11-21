import copy
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from otp_adapter import annotate_v1
from test_fallback_planner import network


def otp_leg():
    return {'mode': 'BUS', 'serviceDate': '2026-10-22', 'route': {'shortName': '1UP'}, 'trip': {'gtfsId': '1:t1'},
            'from': {'stop': {'gtfsId': '1:a'}}, 'to': {'stop': {'gtfsId': '1:c'}}, 'intermediateStops': [{'gtfsId': '1:b'}]}


class StopTimesIndexTests(unittest.TestCase):
    def test_memory_lookup_matches_file_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            planner = network(p)
            from_file, from_memory = {'legs': [otp_leg()]}, {'legs': [otp_leg()]}
            annotate_v1(from_file, p, p/'model.db')
            annotate_v1(from_memory, p, p/'model.db', stop_times=planner.trip_stop_times)
            self.assertEqual(len(from_file['legs'][0]['v1_signals']), 2)
            self.assertEqual(from_memory, from_file)

    def test_rows_keep_after_midnight_times_and_unknown_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            planner = network(Path(tmp))
            planner.sequences['late'] = ((0, 'a', 90600, 90660, '', ''),)
            rows = planner.trip_stop_times({'late', 'missing'})
            self.assertEqual(rows['late'][0]['departure_time'], '25:11:00')
            self.assertEqual(rows['late'][0]['stop_sequence'], '0')
            self.assertEqual(rows['missing'], [])


if __name__ == '__main__':
    unittest.main()
