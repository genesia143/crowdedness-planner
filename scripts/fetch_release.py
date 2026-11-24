"""Download, verify and unpack the submission model and GTFS release assets."""
import argparse
import gzip
import hashlib
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

DEFAULT = 'https://github.com/genesia143/crowdedness-planner/releases/download/v1.0'


def fetch(base, output):
    output = Path(output)
    model, gtfs = output / 'model.db', output / 'gtfs'
    if model.exists() or gtfs.exists():
        raise FileExistsError('model.db or gtfs already exists; choose a new output directory')
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as tmp:
        temp = Path(tmp)
        for name in ('SHA256SUMS', 'model.db.gz', 'gtfs.zip'):
            with urllib.request.urlopen(base.rstrip('/') + '/' + name, timeout=180) as response, (temp / name).open('wb') as dest:
                shutil.copyfileobj(response, dest)
        expected = {}
        for line in (temp / 'SHA256SUMS').read_text(encoding='utf-8').splitlines():
            checksum, filename = line.split(None, 1)
            expected[filename.strip().lstrip('*')] = checksum.lower()
        for name in ('model.db.gz', 'gtfs.zip'):
            digest = hashlib.sha256()
            with (temp / name).open('rb') as f:
                for block in iter(lambda: f.read(1024 * 1024), b''):
                    digest.update(block)
            if digest.hexdigest() != expected.get(name):
                raise ValueError('Checksum mismatch for ' + name)
        extracted = temp / 'gtfs'
        extracted.mkdir()
        with zipfile.ZipFile(temp / 'gtfs.zip') as archive:
            for member in archive.infolist():
                name = member.filename
                if member.is_dir() or '/' in name or '\\' in name or not name.endswith('.txt'):
                    raise ValueError('Unexpected path in GTFS archive: ' + name)
                with archive.open(member) as source, (extracted / name).open('wb') as dest:
                    shutil.copyfileobj(source, dest)
        required = {'stops.txt', 'routes.txt', 'trips.txt', 'stop_times.txt'}
        if not all((extracted / name).is_file() for name in required):
            raise ValueError('GTFS archive is missing required files')
        with gzip.open(temp / 'model.db.gz', 'rb') as source, (temp / 'model.db').open('wb') as dest:
            shutil.copyfileobj(source, dest)
        shutil.move(str(extracted), str(gtfs))
        shutil.move(str(temp / 'model.db'), str(model))
    print('Verified and installed model and GTFS in', output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', default='data/release')
    parser.add_argument('--base-url', default=DEFAULT)
    args = parser.parse_args()
    fetch(args.base_url, args.output_dir)
