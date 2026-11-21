"""Assess 300m exact-name geographic candidates against reviewed mappings.

Counts only ticket occurrences from October 1–21; reviewed mappings are a
convenience-labelled sample, not an unbiased sample of all unmatched tickets.
"""
import argparse
from collections import Counter, defaultdict
from datetime import date, timedelta, timezone
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from model import normalize, parse_timestamp, route_patterns, rows
from reviewed_mappings import inspect


def distance(a, b):
    lat1, lon1 = map(radians, a)
    lat2, lon2 = map(radians, b)
    q = sin((lat2-lat1)/2)**2 + cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2
    return 12742000 * asin(sqrt(min(1, q)))


def evaluate(tickets, gtfs, review):
    names, patterns = route_patterns(gtfs)
    positions = {}
    name_ids = defaultdict(list)
    for r in rows(Path(gtfs) / 'stops.txt'):
        try:
            positions[r['stop_id']] = (float(r['stop_lat']), float(r['stop_lon']))
            name_ids[normalize(r['stop_name'])].append(r['stop_id'])
        except (ValueError, KeyError):
            continue
    labels = {(normalize(r['route']), normalize(r['ticket_stop_name']), r['used_as']): r['stop_id']
              for r in inspect(review, gtfs, confirmed=True) if r['status'] == 'accepted'}
    weights = Counter()
    for row in rows(tickets):
        try:
            t = parse_timestamp(row['created_at'])
            if t.utcoffset() is None or not date(2026,10,1) <= t.astimezone(timezone(timedelta(hours=5,minutes=30))).date() <= date(2026,10,21):
                continue
        except (KeyError, TypeError, ValueError):
            continue
        route = normalize(row.get('route', ''))
        for role, field in (('boarding','start_stop_name'), ('destination','end_stop_name')):
            key = (route, normalize(row.get(field, '')), role)
            if key in labels:
                weights[key] += 1
    totals = Counter()
    for (route, name, role), target in labels.items():
        weight = weights[(route, name, role)]
        if not weight:
            continue
        route_stops = {s for pattern in patterns[route] for s in pattern if s in positions}
        # Focus on stop names absent from this route (already-exact matches need no rescue).
        if any(normalize(names[s]) == name for s in route_stops):
            continue
        totals['reviewed_keys_without_on_route_exact_name'] += 1
        totals['weighted_occurrences'] += weight
        anchors = name_ids.get(name, [])
        if not anchors:
            totals['no_global_exact_name_keys'] += 1
            totals['no_global_exact_name_occurrences'] += weight
            continue
        candidates = {s: min(distance(positions[a], positions[s]) for a in anchors)
                      for s in route_stops}
        candidates = {s:d for s,d in candidates.items() if d <= 300}
        totals['global_name_found_keys'] += 1
        totals['global_name_found_occurrences'] += weight
        if not candidates:
            totals['no_candidate_keys'] += 1
            continue
        totals['candidate_found_keys'] += 1
        totals['candidate_found_occurrences'] += weight
        if len(candidates) > 1:
            totals['multiple_candidate_keys'] += 1
            totals['multiple_candidate_occurrences'] += weight
        if target in candidates:
            totals['reviewed_stop_in_candidates_keys'] += 1
            totals['reviewed_stop_in_candidates_occurrences'] += weight
        if min(candidates, key=candidates.get) == target:
            totals['nearest_matches_review_keys'] += 1
            totals['nearest_matches_review_occurrences'] += weight
        else:
            totals['nearest_disagrees_review_keys'] += 1
            totals['nearest_disagrees_review_occurrences'] += weight
    return totals


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('tickets', 'gtfs', 'review'):
        parser.add_argument('--'+arg, required=True)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.tickets, args.gtfs, args.review), indent=2, sort_keys=True))
