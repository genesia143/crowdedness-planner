"""Diagnose mutually exclusive training-ticket matching failures."""
import argparse
import csv
import json
import sys
from collections import Counter
from datetime import date, timedelta, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from model import StopMatcher, normalize, parse_timestamp, route_patterns, rows
from reviewed_mappings import inspect


def classify(matcher, route, origin, destination):
    route_key = normalize(route)
    if route_key not in matcher.patterns:
        return 'route_unmatched'
    def resolved(value, role):
        if not normalize(value) or normalize(value) in ('null', 'none'):
            return 'missing'
        if (route_key, normalize(value), role) in matcher.reviewed:
            return 'resolved'
        value, _ = matcher.resolve(route_key, value)
        return 'resolved' if value is not None else 'unmatched'
    a, b = resolved(origin, 'boarding'), resolved(destination, 'destination')
    if a != 'resolved' and b != 'resolved':
        return 'both_stops_unresolved'
    if a != 'resolved':
        return 'boarding_stop_missing' if a == 'missing' else 'boarding_stop_unmatched'
    if b != 'resolved':
        return 'destination_stop_missing' if b == 'missing' else 'destination_stop_unmatched'
    segments, _ = matcher.match(route, origin, destination)
    return 'matched' if segments else 'path_unmatched_or_ambiguous'


def diagnose(tickets, gtfs, review, start, end, output):
    start, end = date.fromisoformat(start), date.fromisoformat(end)
    if end < start: raise ValueError('end precedes start')
    names, patterns = route_patterns(gtfs)
    audit = inspect(review, gtfs, confirmed=True)
    reviewed = {(normalize(r['route']), normalize(r['ticket_stop_name']), r['used_as']):r['stop_id'] for r in audit if r['status'] == 'accepted'}
    matcher = StopMatcher(names, patterns, reviewed=reviewed)
    counts, reasons = Counter(), Counter()
    for row in rows(tickets):
        try:
            stamp = parse_timestamp(row['created_at'])
            if stamp.utcoffset() is None: raise ValueError('missing offset')
            day = stamp.astimezone(timezone(timedelta(hours=5, minutes=30))).date()
            if not start <= day <= end: continue
            if int(row['passenger_count']) <= 0: raise ValueError('invalid count')
        except (KeyError, TypeError, ValueError):
            counts['invalid_date_or_count'] += 1
            continue
        category = classify(matcher, row.get('route',''), row.get('start_stop_name',''), row.get('end_stop_name',''))
        counts[category] += 1
        if category != 'matched':
            reasons[(category, row.get('route',''), row.get('start_stop_name',''), row.get('end_stop_name',''))] += 1
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    with open(output/'coverage-summary.json','w',encoding='utf-8') as f:
        json.dump({'start':start.isoformat(),'end':end.isoformat(),'ticket_rows':dict(counts),'note':'invalid timestamps cannot always be assigned to the period'},f,indent=2)
    with open(output/'coverage-unmatched-pairs.csv','w',newline='',encoding='utf-8-sig') as f:
        writer=csv.writer(f); writer.writerow(['reason','route','boarding_name','destination_name','ticket_rows'])
        for (category,route,origin,destination),count in reasons.most_common(): writer.writerow([category,route,origin,destination,count])
    print(json.dumps(dict(counts),indent=2))

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('tickets','gtfs','review','start','end','output'): p.add_argument('--'+name,required=True)
    a=p.parse_args(); diagnose(a.tickets,a.gtfs,a.review,a.start,a.end,a.output)
