import gzip
import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from fetch_release import fetch


class FetchReleaseTests(unittest.TestCase):
    def test_verified_install_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root); assets = root / 'assets'; assets.mkdir()
            (assets / 'model.db.gz').write_bytes(gzip.compress(b'model bytes'))
            with zipfile.ZipFile(assets / 'gtfs.zip', 'w') as z:
                for name in ('stops.txt', 'routes.txt', 'trips.txt', 'stop_times.txt'):
                    z.writestr(name, 'header\n')
            names = ('model.db.gz', 'gtfs.zip')
            (assets / 'SHA256SUMS').write_text(''.join(hashlib.sha256((assets / n).read_bytes()).hexdigest() + '  ' + n + '\n' for n in names))
            target = root / 'output'
            fetch(assets.as_uri(), target)
            self.assertEqual((target / 'model.db').read_bytes(), b'model bytes')
            self.assertTrue((target / 'gtfs' / 'stops.txt').exists())
            with self.assertRaises(FileExistsError):
                fetch(assets.as_uri(), target)

    def test_bad_checksum_does_not_install(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root); assets = root / 'assets'; assets.mkdir()
            (assets / 'model.db.gz').write_bytes(b'invalid')
            (assets / 'gtfs.zip').write_bytes(b'invalid')
            (assets / 'SHA256SUMS').write_text('0' * 64 + '  model.db.gz\n' + '0' * 64 + '  gtfs.zip\n')
            with self.assertRaises(ValueError):
                fetch(assets.as_uri(), root / 'output')
            self.assertFalse((root / 'output' / 'model.db').exists())


if __name__ == '__main__':
    unittest.main()
