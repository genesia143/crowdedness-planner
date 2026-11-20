import argparse
from model import build

parser = argparse.ArgumentParser(description='Build a conservative ticket-derived segment signal')
parser.add_argument('--tickets', required=True)
parser.add_argument('--gtfs', required=True)
parser.add_argument('--start', required=True, help='inclusive local date YYYY-MM-DD')
parser.add_argument('--end', required=True, help='inclusive local date YYYY-MM-DD')
parser.add_argument('--output', required=True)
if __name__ == '__main__':
    args = parser.parse_args()
    result = build(args.tickets, args.gtfs, args.start, args.end, args.output)
    print('Matched {matched} of {total} in-period tickets; wrote {records} daily segment records.'.format(
        matched=result['quality'].get('matched', 0), total=result['quality'].get('in_period', 0), records=len(result['records'])))
