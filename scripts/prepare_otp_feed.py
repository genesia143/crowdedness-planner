#!/usr/bin/env python3
"""Create a small, flat GTFS ZIP for the OpenTripPlanner feasibility trial."""
import argparse
import csv
import io
from pathlib import Path
import zipfile


def prepare(source, destination, route_names):
    source, destination = Path(source), Path(destination)
    required = {'agency.txt', 'routes.txt', 'trips.txt', 'stop_times.txt', 'stops.txt'}
    with zipfile.ZipFile(source) as archive:
        members = {}
        for info in archive.infolist():
            if info.is_dir() or not info.filename.lower().endswith('.txt'):
                continue
            name = Path(info.filename).name
            if name in members:
                raise ValueError(f'Ambiguous GTFS file: {name}')
            members[name] = info
        missing = required - members.keys()
        if missing:
            raise ValueError(f'Missing GTFS files: {", ".join(sorted(missing))}')

        def rows(name):
            with archive.open(members[name]) as raw:
                with io.TextIOWrapper(raw, encoding='utf-8-sig', newline='') as text:
                    yield from csv.DictReader(text)

        routes = [r for r in rows('routes.txt') if r['route_short_name'] in route_names]
        found = {r['route_short_name'] for r in routes}
        if found != route_names:
            raise ValueError(f'Routes not found: {", ".join(sorted(route_names - found))}')
        route_ids = {r['route_id'] for r in routes}
        trips = [r for r in rows('trips.txt') if r['route_id'] in route_ids]
        if not trips:
            raise ValueError('Selected routes have no trips')
        trip_ids = {r['trip_id'] for r in trips}
        shape_ids = {r.get('shape_id') for r in trips} - {None, ''}
        stop_times = [r for r in rows('stop_times.txt') if r['trip_id'] in trip_ids]
        stop_ids = {r['stop_id'] for r in stop_times}
        if not stop_ids:
            raise ValueError('Selected trips have no stop times')
        stops = list(rows('stops.txt'))
        all_ids = [r['stop_id'] for r in stops]
        if len(set(all_ids)) != len(all_ids):
            raise ValueError('Duplicate stop IDs in input feed')
        if stop_ids - set(all_ids):
            raise ValueError('Selected trips refer to missing stops')
        stops = [r for r in stops if r['stop_id'] in stop_ids]
        shapes = [r for r in rows('shapes.txt') if r['shape_id'] in shape_ids] if 'shapes.txt' in members else []
        if shape_ids and {r['shape_id'] for r in shapes} != shape_ids:
            raise ValueError('Selected trips refer to missing shapes')
        # Exclusive creation protects the source and existing work from replacement.
        with destination.open('xb') as output:
            with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as result:
                filtered = {'routes.txt': routes, 'trips.txt': trips, 'stop_times.txt': stop_times, 'stops.txt': stops}
                if shapes:
                    filtered['shapes.txt'] = shapes
                for name, data in filtered.items():
                    buffer = io.StringIO(newline='')
                    writer = csv.DictWriter(buffer, fieldnames=data[0].keys(), lineterminator='\n')
                    writer.writeheader()
                    writer.writerows(data)
                    result.writestr(name, buffer.getvalue())
                for name in ('agency.txt', 'calendar.txt', 'calendar_dates.txt', 'feed_info.txt'):
                    if name in members:
                        result.writestr(name, archive.read(members[name]))
    return len(routes), len(trips), len(stops)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', help='Original GTFS ZIP (nested directories are accepted)')
    parser.add_argument('destination', help='New output ZIP; must not already exist')
    parser.add_argument('--routes', required=True, help='Comma-separated route_short_name values')
    args = parser.parse_args()
    route_names = {name.strip() for name in args.routes.split(',') if name.strip()}
    if not route_names:
        parser.error('Specify at least one route')
    counts = prepare(args.source, args.destination, route_names)
    print(f'Created {args.destination}: {counts[0]} routes, {counts[1]} trips, {counts[2]} stops')


if __name__ == '__main__':
    main()
