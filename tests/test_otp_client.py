import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from otp_client import plan, timing_breakdown, signal_coverage, journey_crowding_summary
from datetime import datetime

class OtpClientTests(unittest.TestCase):
    @patch('otp_client.annotate_v1')
    @patch('otp_client.urlopen')
    def test_filters_and_annotates_bus_journeys(self, urlopen, annotate):
        def itinerary(distance):
            return {'legs':[{'mode':'BUS'}, {'mode':'WALK','distance':distance}, {'mode':'BUS'}]}
        payload={'data':{'planConnection':{'edges':[{'node':itinerary(1000)}, {'node':itinerary(1001)}, {'node':{'legs':[{'mode':'WALK'}]}}]}}}
        urlopen.return_value.__enter__.return_value=io.BytesIO(json.dumps(payload).encode())
        result=plan('http://localhost', '.', 'unused', 28.6, 77.2, 28.5, 77.3, '2026-10-22T08:00:00+05:30')
        self.assertEqual(len(result['journeys']),1)
        self.assertEqual(result['excluded_bus_candidates'],1)
        annotate.assert_called_once()

    def test_walking_and_waiting_breakdown(self):
        def leg(mode, start, end):
            return {'mode':mode, 'start':{'scheduledTime':'2026-10-22T'+start+'+05:30'}, 'end':{'scheduledTime':'2026-10-22T'+end+'+05:30'}}
        journey = {'legs':[leg('BUS','08:05:00','08:20:00'), leg('WALK','08:20:00','08:27:00'), leg('BUS','08:35:00','08:50:00')]}
        timing_breakdown(journey, datetime.fromisoformat('2026-10-22T08:00:00+05:30'))
        summary=journey['timing_summary']
        self.assertEqual(summary['walking_minutes'],7)
        self.assertEqual(summary['bus_minutes'],30)
        self.assertEqual(summary['waiting_minutes'],13)
        self.assertEqual(summary['status'],'available')

    def test_rejects_invalid_inputs(self):
        with self.assertRaises(ValueError):
            plan('http://localhost', '.', 'unused', 'nan', 77, 28, 77, '2026-10-22T08:00:00+05:30')
        with self.assertRaises(ValueError):
            plan('http://localhost', '.', 'unused', 28, 77, 28, 77, '2026-10-22T08:00:00')

    def test_inconsistent_timing_is_not_reported_as_a_valid_summary(self):
        def leg(mode, start, end):
            return {'mode': mode, 'start': {'scheduledTime': '2026-10-22T' + start + '+05:30'},
                    'end': {'scheduledTime': '2026-10-22T' + end + '+05:30'}}
        journey = {'legs': [leg('BUS', '08:05:00', '08:20:00'),
                            leg('WALK', '08:19:00', '08:25:00'),
                            leg('BUS', '08:35:00', '08:50:00')]}
        timing_breakdown(journey, datetime.fromisoformat('2026-10-22T08:00:00+05:30'))
        self.assertEqual(journey['timing_summary']['status'], 'incomplete or inconsistent leg times')
        self.assertIsNone(journey['timing_summary']['waiting_minutes'])
        self.assertIsNone(journey['timing_summary']['walking_minutes'])

    def test_coverage_does_not_count_unobserved_zero_as_evidence(self):
        journey = {'legs': [
            {'mode': 'BUS', 'v1_signals': [
                {'status': 'available', 'all_scheduled_days_proxy': {'sample_passengers_per_scheduled_crossing': 0.2}},
                {'status': 'unavailable', 'all_scheduled_days_proxy': {'sample_passengers_per_scheduled_crossing': 0}},
                {'status': 'available', 'all_scheduled_days_proxy': None},
            ]},
            {'mode': 'WALK'},
            {'mode': 'BUS', 'v1_signals': []},
        ]}
        signal_coverage(journey)
        summary = journey['signal_coverage']
        self.assertEqual(summary['segments_with_observations_and_service'], 1)
        self.assertEqual(summary['segments_without_observations_or_service'], 2)
        self.assertEqual(summary['bus_legs_without_segment_details'], 1)

    def test_journey_summary_preserves_partial_and_route_specific_evidence(self):
        journey = {'legs': [
            {'mode': 'BUS', 'route': {'shortName': '8UP'}, 'v1_signals': [
                {'status': 'available', 'relative_crowding': {'label': 'likely busier'}},
                {'status': 'available', 'relative_crowding': {'label': 'insufficient evidence'}},
                {'status': 'unavailable', 'relative_crowding': {'label': 'likely quieter'}},
            ]},
            {'mode': 'WALK'},
            {'mode': 'BUS', 'route': {'shortName': '405UP'}, 'v1_signals': []},
        ]}
        journey_crowding_summary(journey)
        summary = journey['crowding_summary']
        self.assertEqual(summary['status'], 'partial evidence')
        self.assertEqual(summary['labelled_segments'], 1)
        self.assertEqual(summary['segments_without_label'], 2)
        self.assertEqual(summary['bus_legs_without_segment_details'], 1)
        self.assertEqual(summary['bus_legs'][0]['segment_label_counts']['likely busier'], 1)
        self.assertEqual(summary['bus_legs'][1]['route'], '405UP')
        self.assertNotIn('label', summary)

    def test_journey_summary_reports_insufficient_evidence_when_no_labels(self):
        journey = {'legs': [{'mode': 'BUS', 'v1_signals': []}]}
        journey_crowding_summary(journey)
        self.assertEqual(journey['crowding_summary']['status'], 'insufficient evidence')

if __name__ == '__main__': unittest.main()
