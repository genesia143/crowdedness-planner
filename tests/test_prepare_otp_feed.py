import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.prepare_otp_feed import prepare


class PrepareOtpFeedTest(unittest.TestCase):
    def test_subset_preserves_ids_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / 'source.zip', Path(folder) / 'output.zip'
            with zipfile.ZipFile(source, 'w') as feed:
                feed.writestr('nested/agency.txt', 'agency_id,agency_name\nA,Agency\n')
                feed.writestr('nested/routes.txt', 'route_id,route_short_name\n1,8UP\n2,9UP\n')
                feed.writestr('nested/trips.txt', 'route_id,trip_id,shape_id\n1,t1,s1\n2,t2,s2\n')
                feed.writestr('nested/stop_times.txt', 'trip_id,stop_id,stop_sequence\nt1,001,1\nt1,002,2\nt2,003,1\n')
                feed.writestr('nested/stops.txt', 'stop_id,stop_name\n001,A\n002,B\n003,C\n')
                feed.writestr('nested/shapes.txt', 'shape_id,shape_pt_lat\ns1,28.5\ns2,28.6\n')
            self.assertEqual(prepare(source, output, {'8UP'}), (1, 1, 2))
            with zipfile.ZipFile(output) as feed:
                self.assertIn('001,A', feed.read('stops.txt').decode())
                self.assertNotIn('003,C', feed.read('stops.txt').decode())
                self.assertNotIn('t2', feed.read('trips.txt').decode())
            with self.assertRaises(FileExistsError):
                prepare(source, output, {'8UP'})
            with self.assertRaisesRegex(ValueError, 'Routes not found'):
                prepare(source, Path(folder) / 'missing.zip', {'missing'})


if __name__ == '__main__':
    unittest.main()
