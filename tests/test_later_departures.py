import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from api import mapped_journeys


class Planner:
    def plan(self, lat1, lon1, lat2, lon2, departure, walk):
        minute = departure[14:16]
        end = '09:30' if minute == '00' else '09:40'
        journey = {'start': '2026-10-22T09:00:00+05:30',
                   'end': '2026-10-22T' + end + ':00+05:30',
                   'legs': [{'mode': 'BUS', 'start': {'scheduledTime': '2026-10-22T09:00:00+05:30'},
                             'end': {'scheduledTime': '2026-10-22T' + end + ':00+05:30'},
                             'route': {'shortName': minute}}]}
        return {'journeys': [journey], 'routing_source': 'built-in'}


class LaterDepartureTests(unittest.TestCase):
    def test_search_combines_later_results_and_uses_original_wait(self):
        params = {k: [v] for k, v in {'from_lat': '28.6', 'from_lon': '77.2',
                  'to_lat': '28.5', 'to_lon': '77.2',
                  'departure': '2026-10-22T08:50:00+05:30', 'extra_minutes': '5'}.items()}
        result = mapped_journeys(params, None, None, None, None, None, Planner())
        self.assertEqual(result['search_coverage']['departure_offsets_minutes_completed'], [0, 10, 20])
        self.assertFalse(result['search_coverage']['exhaustive'])
        self.assertEqual(result['choices']['fastest_index'], 1)
        self.assertEqual(result['choices']['eligible_indices'], [1])
        self.assertEqual(result['journeys'][1]['timing_summary']['waiting_minutes'], 10)


if __name__ == '__main__':
    unittest.main()
