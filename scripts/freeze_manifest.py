"""Create or verify an immutable-input manifest before the final evaluation.

This tool does not inspect tickets or evaluate a model. Pass only the trained
index, GTFS and reviewed mappings, and the exact source/evaluation files used.
Creating a manifest records a proposed snapshot; it does not approve a model.
"""
import argparse
import hashlib
import json
from pathlib import Path


def fingerprint(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError(f'symlinks are not supported: {path}')
    if path.is_file():
        files = [path]
        root = path.parent
    elif path.is_dir():
        root = path
        files = sorted(p for p in root.rglob('*')
                       if '__pycache__' not in p.relative_to(root).parts
                       and p.suffix != '.pyc' and (p.is_file() or p.is_symlink()))
        if not files:
            raise ValueError(f'empty directory: {path}')
        if any(p.is_symlink() for p in files):
            raise ValueError(f'directory contains symlinks: {path}')
    else:
        raise ValueError(f'input does not exist: {path}')
    digest = hashlib.sha256()
    # Length-prefixed names and per-file contents prevent ambiguous concatenation.
    for file in files:
        name = file.relative_to(root).as_posix().encode('utf-8')
        digest.update(len(name).to_bytes(8, 'big'))
        digest.update(name)
        content_hash = hashlib.sha256()
        with file.open('rb') as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                content_hash.update(chunk)
        digest.update(content_hash.digest())
    return {'sha256': digest.hexdigest(), 'files': len(files)}


def snapshot(inputs):
    if not inputs:
        raise ValueError('at least one named input is required')
    return {'schema_version': 1, 'purpose': 'proposed pre-holdout input snapshot',
            'inputs': {name: fingerprint(path) for name, path in sorted(inputs.items())}}


def verify(manifest, inputs):
    expected = json.loads(Path(manifest).read_text(encoding='utf-8'))
    return expected == snapshot(inputs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('create', 'verify'))
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--input', action='append', required=True, metavar='NAME=PATH')
    args = parser.parse_args()
    inputs = {}
    for spec in args.input:
        name, sep, path = spec.partition('=')
        if not sep or not name or not path or name in inputs:
            parser.error('inputs must have distinct, nonempty NAME=PATH values')
        inputs[name] = path
    if args.action == 'create':
        content = json.dumps(snapshot(inputs), indent=2, sort_keys=True) + '\n'
        with args.manifest.open('x', encoding='utf-8') as handle:
            handle.write(content)
        print('Proposed snapshot written; model selection remains a separate decision.')
    elif verify(args.manifest, inputs):
        print('All inputs match the proposed snapshot.')
    else:
        raise SystemExit('Input mismatch: do not run the final evaluation.')


if __name__ == '__main__':
    main()
