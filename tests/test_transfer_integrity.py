"""Transfer paths must not silently bridge different bus stops."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from otp_adapter import transfer_walks_within_limit


def bus(origin, destination):
    return {'mode': 'BUS', 'from': {'stop': {'gtfsId': 'feed:' + origin}},
            'to': {'stop': {'gtfsId': 'feed:' + destination}}}


class TransferIntegrityTests(unittest.TestCase):
    def test_consecutive_buses_at_same_stop_need_no_walking_leg(self):
        self.assertTrue(transfer_walks_within_limit([bus('A', 'B'), bus('B', 'C')], 1000))

    def test_consecutive_buses_at_different_stops_need_transfer_evidence(self):
        self.assertFalse(transfer_walks_within_limit([bus('A', 'B'), bus('C', 'D')], 1000))


if __name__ == '__main__':
    unittest.main()
