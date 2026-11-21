import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from reviewed_mappings import inspect, write_report

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--review', required=True)
    parser.add_argument('--gtfs', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--confirm-review', action='store_true')
    args = parser.parse_args()
    print(dict(write_report(inspect(args.review, args.gtfs, confirmed=args.confirm_review), args.output)))
