#!/usr/bin/env python3
"""Create the experimental Delhi-region OSM extract (requires pyosmium)."""
import argparse
from pathlib import Path
import osmium


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--regional', required=True, help='Source OSM PBF (India-wide recommended)')
    parser.add_argument('--city', help='Optional city OSM PBF to merge for experiments')
    parser.add_argument('--output-dir', required=True, help='New directory for intermediate and merged extracts')
    args = parser.parse_args()
    folder = Path(args.output_dir)
    folder.mkdir(parents=True, exist_ok=False)
    regional = folder / 'regional-clipped.osm.pbf'
    combined = folder / 'combined.osm.pbf'
    with osmium.ForwardReferenceWriter(str(regional), args.regional, back_references=True, remove_tags=False, forward_relation_depth=0) as writer:
        class Clip(osmium.SimpleHandler):
            def node(self, node):
                if node.location.valid() and 28.15 <= node.location.lat <= 29.40 and 76.53 <= node.location.lon <= 77.50:
                    writer.add_node(node)
        Clip().apply_file(args.regional)
    if args.city:
        reader = osmium.MergeInputReader()
        reader.add_file(str(regional))
        reader.add_file(args.city)
        with osmium.SimpleWriter(str(combined)) as writer:
            reader.apply(writer, simplify=True)
        result = combined
    else:
        result = regional
    print(f'Created {result}; validate stop linkage and walking paths before use.')


if __name__ == '__main__':
    main()
