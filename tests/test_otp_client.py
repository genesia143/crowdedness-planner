import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from otp_client import plan, timing_breakdown
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

if __name__ == '__main__': unittest.main()
