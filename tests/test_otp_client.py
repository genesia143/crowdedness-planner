import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from otp_client import plan

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

    def test_rejects_invalid_inputs(self):
        with self.assertRaises(ValueError):
            plan('http://localhost', '.', 'unused', 'nan', 77, 28, 77, '2026-10-22T08:00:00+05:30')
        with self.assertRaises(ValueError):
            plan('http://localhost', '.', 'unused', 28, 77, 28, 77, '2026-10-22T08:00:00')

if __name__ == '__main__': unittest.main()
