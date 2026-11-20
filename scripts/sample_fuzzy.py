"""Create a reproducible, ticket-row-weighted fuzzy matching review sample."""
import argparse
import csv
import random
import sys
from datetime import date, timedelta, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from model import StopMatcher, normalize, parse_timestamp, route_patterns, rows


def sample(tickets, gtfs, start, end, output, size=100, seed=42):
    start, end = date.fromisoformat(start), date.fromisoformat(end)
    names, patterns = route_patterns(gtfs)
    matcher = StopMatcher(names, patterns, fuzzy=True)
    rng = random.Random(seed)
    chosen, eligible = [], 0
    for row in rows(tickets):
        try:
            timestamp = parse_timestamp(row['created_at'])
            if timestamp.utcoffset() is None:
                continue
            day = timestamp.astimezone(timezone(timedelta(hours=5, minutes=30))).date()
            if not start <= day <= end or int(row['passenger_count']) <= 0:
                continue
        except (ValueError, TypeError, KeyError):
            continue
        segments, method = matcher.match(row.get('route',''), row.get('start_stop_name',''), row.get('end_stop_name',''))
        if method != 'fuzzy':
            continue
        eligible += 1
        route = normalize(row['route'])
        resolved_start, _ = matcher.resolve(route, row['start_stop_name'])
        resolved_end, _ = matcher.resolve(route, row['end_stop_name'])
        item = {'route': row['route'], 'ticket_start': row['start_stop_name'], 'matched_start': resolved_start,
                'ticket_end': row['end_stop_name'], 'matched_end': resolved_end,
                'first_stop_id': segments[0][0], 'last_stop_id': segments[-1][1],
                'review_correct': '', 'review_notes': ''}
        if len(chosen) < size:
            chosen.append(item)
        else:
            slot = rng.randrange(eligible)
            if slot < size:
                chosen[slot] = item
    fields = ['route','ticket_start','matched_start','ticket_end','matched_end','first_stop_id','last_stop_id','review_correct','review_notes']
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    with open(output, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(chosen)
    print('Sampled {} ticket rows from {} fuzzy-matched training rows (seed {}).'.format(len(chosen), eligible, seed))

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--tickets', required=True); p.add_argument('--gtfs', required=True)
    p.add_argument('--start', required=True); p.add_argument('--end', required=True); p.add_argument('--output', required=True)
    p.add_argument('--size', type=int, default=100); p.add_argument('--seed', type=int, default=42)
    a = p.parse_args()
    if a.size <= 0: p.error('size must be positive')
    sample(a.tickets, a.gtfs, a.start, a.end, a.output, a.size, a.seed)
