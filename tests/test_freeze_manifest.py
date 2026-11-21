import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


spec = importlib.util.spec_from_file_location('freeze_manifest', Path(__file__).resolve().parents[1] / 'scripts/freeze_manifest.py')
freeze = importlib.util.module_from_spec(spec)
spec.loader.exec_module(freeze)


class FreezeManifestTests(unittest.TestCase):
    def test_detects_change_and_added_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            gtfs = root / 'gtfs'
            gtfs.mkdir()
            (gtfs / 'stops.txt').write_text('original', encoding='utf-8')
            model = root / 'index.db'
            model.write_bytes(b'model')
            inputs = {'gtfs': gtfs, 'model': model}
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps(freeze.snapshot(inputs)), encoding='utf-8')
            self.assertTrue(freeze.verify(manifest, inputs))
            (gtfs / 'new.txt').write_text('new', encoding='utf-8')
            self.assertFalse(freeze.verify(manifest, inputs))
            (gtfs / 'new.txt').unlink()
            model.write_bytes(b'changed')
            self.assertFalse(freeze.verify(manifest, inputs))

    def test_rejects_symlinks_and_empty_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'a').write_text('data', encoding='utf-8')
            (root / 'link').symlink_to(root / 'a')
            with self.assertRaises(ValueError):
                freeze.fingerprint(root)
            with self.assertRaises(ValueError):
                freeze.snapshot({})


if __name__ == '__main__':
    unittest.main()
