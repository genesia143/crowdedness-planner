import argparse
from predict import create_database

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Index daily segment counts for the prototype API')
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--gtfs', help='GTFS directory for scheduled-service denominator')
    args = parser.parse_args()
    create_database(args.input, args.output, gtfs=args.gtfs)
