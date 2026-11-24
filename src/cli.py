import argparse
from model import build

parser = argparse.ArgumentParser(description='Build a conservative ticket-derived segment signal')
parser.add_argument('--tickets', required=True)
parser.add_argument('--gtfs', required=True)
parser.add_argument('--start', required=True, help='inclusive local date YYYY-MM-DD')
parser.add_argument('--end', required=True, help='inclusive local date YYYY-MM-DD')
parser.add_argument('--output', required=True)
parser.add_argument('--confirm-review', action='store_true', help='use reviewed IDs despite similarity warnings; structural checks still apply')
parser.add_argument('--review', help='reviewed XLSX or CSV with route-checked GTFS stop IDs')
parser.add_argument('--segment-timing', action='store_true', help='experimental median GTFS travel-time offsets')
parser.add_argument('--fuzzy', action='store_true', help='experimental fuzzy stop matching; requires independent review')
if __name__ == '__main__':
    args = parser.parse_args()
    result = build(args.tickets, args.gtfs, args.start, args.end, args.output, fuzzy=args.fuzzy, segment_timing=args.segment_timing, review_file=args.review, confirm_review=args.confirm_review)
    print('Matched {matched} of {total} in-period tickets; wrote {records} daily segment records.'.format(
        matched=result['quality'].get('matched', 0), total=result['quality'].get('in_period', 0), records=len(result['records'])))
