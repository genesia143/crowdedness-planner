"""Prepare a training-only, route-conditioned stop-name review queue."""
import argparse
import csv
import sys
from collections import Counter
from datetime import date, timedelta, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from model import StopMatcher, normalize, parse_timestamp, route_patterns, rows


def prepare(tickets, gtfs, start, end, output, limit=250):
    start, end = date.fromisoformat(start), date.fromisoformat(end)
    if start > end:
        raise ValueError('start must not follow end')
    names, patterns = route_patterns(gtfs)
    matcher = StopMatcher(names, patterns, fuzzy=True)
    counts = Counter()
    for row in rows(tickets):
        try:
            created = parse_timestamp(row['created_at'])
            if created.utcoffset() is None:
                continue
            day = created.astimezone(timezone(timedelta(hours=5, minutes=30))).date()
            if not start <= day <= end or int(row['passenger_count']) <= 0:
                continue
        except (ValueError, TypeError, KeyError):
            continue
        for role, field in [('boarding', 'start_stop_name'), ('destination', 'end_stop_name')]:
            counts[(row.get('route', ''), row.get(field, ''), role)] += 1
    result = []
    for (route, name, role), count in counts.items():
        route_key = normalize(route)
        if route_key not in patterns:
            continue
        resolved, kind = matcher.resolve(route_key, name)
        if kind == 'exact':
            continue
        ids = sorted({stop for pattern in patterns[route_key] for stop in pattern if resolved is not None and normalize(names[stop]) == resolved})
        result.append({'route': route, 'ticket_stop_name': name, 'used_as': role, 'ticket_rows': count,
                       'suggested_gtfs_name': resolved or '', 'candidate_gtfs_stop_ids': ' | '.join(ids),
                       'suggestion_type': kind, 'decision': '', 'correct_gtfs_stop_id': '', 'notes': ''})
    result.sort(key=lambda row: (-row['ticket_rows'], row['route'], row['ticket_stop_name'], row['used_as']))
    fields = ['route','ticket_stop_name','used_as','ticket_rows','suggested_gtfs_name','candidate_gtfs_stop_ids','suggestion_type','decision','correct_gtfs_stop_id','notes']
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    with open(output, 'w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(result[:limit])
    print('Wrote {} of {} route/name/role combinations; training dates {} to {}.'.format(min(limit, len(result)), len(result), start, end))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tickets', required=True); p.add_argument('--gtfs', required=True)
    p.add_argument('--start', required=True); p.add_argument('--end', required=True); p.add_argument('--output', required=True)
    p.add_argument('--limit', type=int, default=250)
    a = p.parse_args()
    if a.limit <= 0: p.error('limit must be positive')
    prepare(a.tickets, a.gtfs, a.start, a.end, a.output, a.limit)
