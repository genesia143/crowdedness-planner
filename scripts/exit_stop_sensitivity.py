"""Development-only sensitivity of sample segment flows to changed exit stops."""
import argparse
from collections import Counter
from datetime import date, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from model import StopMatcher, normalize, parse_timestamp, route_patterns, rows
from reviewed_mappings import inspect


def evaluate(tickets, gtfs, review):
    names, patterns = route_patterns(gtfs)
    reviewed = {(normalize(r['route']), normalize(r['ticket_stop_name']), r['used_as']): r['stop_id']
                for r in inspect(review, gtfs, confirmed=True) if r['status'] == 'accepted'}
    matcher = StopMatcher(names, patterns, reviewed=reviewed)
    counts = Counter()
    unique_paths = {}
    for row in rows(tickets):
        try:
            t = parse_timestamp(row['created_at'])
            if t.utcoffset() is None:
                continue
            day = t.astimezone(timezone(timedelta(hours=5, minutes=30))).date()
            if not date(2026, 10, 1) <= day <= date(2026, 10, 21):
                continue
            pax = int(row['passenger_count'])
            if pax <= 0:
                continue
        except (KeyError, TypeError, ValueError):
            continue
        route = normalize(row.get('route', ''))
        path, _ = matcher.match(route, row.get('start_stop_name', ''), row.get('end_stop_name', ''))
        if not path:
            continue
        counts['matched_tickets'] += 1
        counts['matched_passengers'] += pax
        counts['baseline_passenger_segments'] += pax * len(path)
        if len(path) > 1:
            counts['earlier_adjustable_tickets'] += 1
            counts['earlier_removed_passenger_segments'] += pax
        else:
            counts['earlier_one_segment_unadjustable'] += 1
        key = (route, path)
        if key not in unique_paths:
            extensions = set()
            stops = (path[0][0],) + tuple(pair[1] for pair in path)
            for pattern in patterns[route]:
                n = len(stops)
                for i in range(len(pattern) - n + 1):
                    if pattern[i:i+n] == stops and i+n < len(pattern):
                        extensions.add(pattern[i+n])
            unique_paths[key] = len(extensions) == 1
        if unique_paths[key]:
            counts['later_adjustable_tickets'] += 1
            counts['later_added_passenger_segments'] += pax
        else:
            counts['later_terminal_or_ambiguous'] += 1
    return counts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('tickets', 'gtfs', 'review'):
        parser.add_argument('--' + arg, required=True)
    args = parser.parse_args()
    result = evaluate(args.tickets, args.gtfs, args.review)
    import json
    print(json.dumps(result, indent=2, sort_keys=True))
