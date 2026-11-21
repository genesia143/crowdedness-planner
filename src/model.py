"""Conservative ticket-derived segment signal; Python standard library only."""
import csv
from difflib import SequenceMatcher
from functools import lru_cache
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path


def normalize(value):
    return re.sub(r'[^a-z0-9]+', ' ', (value or '').lower()).strip()


def day_type(day):
    """Calendar day classification; public holidays are not separately modelled."""
    return ('weekday', 'weekday', 'weekday', 'weekday', 'weekday', 'saturday', 'sunday')[day.weekday()]


def parse_timestamp(value):
    # Python 3.9 accepts only three or six fractional digits in fromisoformat.
    # Pad shorter decimal fractions without changing their meaning.
    value = re.sub(r"\.(\d{1,6})(?=Z|[+-]\d{2}:\d{2}$|$)",
                   lambda match: "." + match.group(1).ljust(6, "0"), value)
    if value.endswith('Z'):
        value = value[:-1] + '+00:00'
    return datetime.fromisoformat(value)


def critical_tokens(value):
    """Protect directional words and block identifiers from fuzzy substitution."""
    text = normalize(value)
    directions = frozenset(re.findall(r'\b(?:east|west|north|south)\b', text))
    block = re.search(r'\b([a-z0-9]+)\s+block\b|\bblock\s+([a-z0-9]+)\b', text)
    return directions, (block.group(1) or block.group(2)) if block else None


def rows(path):
    with open(path, encoding='utf-8-sig', newline='') as handle:
        header = handle.readline()
        handle.seek(0)
        yield from csv.DictReader(handle, delimiter='\t' if '\t' in header else ',')


def route_patterns(gtfs):
    gtfs = Path(gtfs)
    names = {}
    for stop in rows(gtfs / 'stops.txt'):
        stop_id = stop['stop_id']
        if stop_id in names:
            raise ValueError('duplicate GTFS stop_id: ' + stop_id)
        names[stop_id] = stop['stop_name']
    routes = {r['route_id']: r['route_short_name'] for r in rows(gtfs / 'routes.txt')}
    trips = {r['trip_id']: routes.get(r['route_id']) for r in rows(gtfs / 'trips.txt')}
    stops = defaultdict(list)
    for row in rows(gtfs / 'stop_times.txt'):
        if row['trip_id'] in trips and row['stop_id'] in names:
            stops[row['trip_id']].append((int(row['stop_sequence']), row['stop_id']))
    patterns = defaultdict(set)
    for trip, sequence in stops.items():
        route = trips[trip]
        if route:
            patterns[normalize(route)].add(tuple(stop for _, stop in sorted(sequence)))
    return names, patterns


def match_segments(route, start, end, names, patterns):
    candidates = set()
    for pattern in patterns.get(normalize(route), ()):
        for i, stop in enumerate(pattern):
            if normalize(names[stop]) != normalize(start):
                continue
            for j in range(i + 1, len(pattern)):
                if normalize(names[pattern[j]]) == normalize(end):
                    candidates.add(tuple(zip(pattern[i:j], pattern[i+1:j+1])))
    return next(iter(candidates)) if len(candidates) == 1 else None



class StopMatcher:
    """Route-scoped exact matching with an optional conservative fuzzy fallback."""
    def __init__(self, names, patterns, fuzzy=False, reviewed=None):
        self.names, self.patterns, self.fuzzy = names, patterns, fuzzy
        self.reviewed = reviewed or {}
        self.route_names = {}
        for route, variants in patterns.items():
            self.route_names[route] = sorted({normalize(names[s]) for p in variants for s in p})

    @lru_cache(maxsize=200000)
    def resolve(self, route, value):
        candidates = self.route_names.get(route, ())
        value = normalize(value)
        if not value or value in ('null', 'none'):
            return None, 'missing'
        if value in candidates:
            return value, 'exact'
        if not self.fuzzy:
            return None, 'unmatched'
        ranked = sorted(((SequenceMatcher(None, value, candidate).ratio(), candidate)
                         for candidate in candidates), reverse=True)
        # A high score alone is insufficient when two different stops look alike.
        if not ranked or ranked[0][0] < 0.90:
            return None, 'unmatched'
        if critical_tokens(value) != critical_tokens(ranked[0][1]):
            return None, 'ambiguous'
        if len(ranked) > 1 and ranked[0][0] - ranked[1][0] < 0.08:
            return None, 'ambiguous'
        return ranked[0][1], 'fuzzy'

    @lru_cache(maxsize=200000)
    def match(self, route, start, end):
        route = normalize(route)
        if route not in self.patterns:
            return None, 'route_unmatched'
        start_id = self.reviewed.get((route, normalize(start), 'boarding'))
        end_id = self.reviewed.get((route, normalize(end), 'destination'))
        start_name, start_kind = (None, 'reviewed') if start_id else self.resolve(route, start)
        end_name, end_kind = (None, 'reviewed') if end_id else self.resolve(route, end)
        if (start_id is None and start_name is None) or (end_id is None and end_name is None):
            return None, 'stop_unmatched_or_ambiguous'
        candidates = set()
        for pattern in self.patterns[route]:
            for i, stop in enumerate(pattern):
                if not (stop == start_id if start_id is not None else normalize(self.names[stop]) == start_name):
                    continue
                for j in range(i + 1, len(pattern)):
                    target = pattern[j]
                    if target == end_id if end_id is not None else normalize(self.names[target]) == end_name:
                        candidates.add(tuple(zip(pattern[i:j], pattern[i+1:j+1])))
        if len(candidates) != 1:
            return None, 'path_unmatched_or_ambiguous'
        method = 'reviewed' if 'reviewed' in (start_kind, end_kind) else ('fuzzy' if 'fuzzy' in (start_kind, end_kind) else 'exact')
        return next(iter(candidates)), method

def build(tickets, gtfs, start_date, end_date, output, fuzzy=False, segment_timing=False, review_file=None, confirm_review=False):
    start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
    if end < start:
        raise ValueError('end date must not precede start date')
    names, patterns = route_patterns(gtfs)
    counts, quality = Counter(), Counter()
    reviewed = {}
    audit = []
    if review_file:
        from reviewed_mappings import inspect
        audit = inspect(review_file, gtfs, confirmed=confirm_review)
        reviewed = {(normalize(r['route']), normalize(r['ticket_stop_name']), r['used_as']): r['stop_id'] for r in audit if r['status'] == 'accepted'}
    matcher = StopMatcher(names, patterns, fuzzy=fuzzy, reviewed=reviewed)
    if segment_timing:
        from timing import ScheduleOffsets
        offsets = ScheduleOffsets(gtfs)
    for row in rows(tickets):
        try:
            timestamp = parse_timestamp(row['created_at'])
            if timestamp.utcoffset() is None:
                raise ValueError('timestamp must include an offset')
            # Ticket timestamps in this dataset are in IST. Normalize offsets before assigning the date.
            from datetime import timedelta, timezone
            timestamp = timestamp.astimezone(timezone(timedelta(hours=5, minutes=30)))
            if not start <= timestamp.date() <= end:
                continue
            passengers = int(row['passenger_count'])
            if passengers <= 0:
                raise ValueError('passenger count must be positive')
        except (KeyError, TypeError, ValueError):
            quality['invalid_date_or_count'] += 1
            continue
        quality['in_period'] += 1
        key = (row.get('route', ''), row.get('start_stop_name', ''), row.get('end_stop_name', ''))
        segments, method = matcher.match(*key)
        quality[method] += 1
        if not segments:
            continue
        quality['matched'] += 1
        travel = offsets.offsets(key[0], segments) if segment_timing else (0,) * len(segments)
        if travel is None:
            quality['timing_unavailable'] += 1
            continue
        for (a, b), seconds in zip(segments, travel):
            crossing = timestamp + timedelta(seconds=seconds)
            # Do not leak post-training segment times into a training artifact.
            if not start <= crossing.date() <= end:
                quality['segment_outside_period'] += 1
                continue
            kind = day_type(crossing)
            counts[(normalize(key[0]), a, b, crossing.date().isoformat(), crossing.hour, kind)] += passengers
    result = {'definition': ('ticket-sample passenger journeys by estimated segment crossing hour using median scheduled offset' if segment_timing else 'observed ticket-sample passenger journeys crossing a segment, grouped by ticket boarding hour'),
              'training_start': start_date, 'training_end': end_date, 'fuzzy_enabled': fuzzy, 'segment_timing': segment_timing, 'reviewed_mapping_count': len(reviewed), 'review_similarity_flags_confirmed': confirm_review, 'review_rows_flagged': sum(r['status'] != 'accepted' for r in audit), 'quality': dict(quality),
              'records': [{'route': route, 'from_stop_id': a, 'to_stop_id': b, 'date': day,
                           'hour': hour, 'day_type': kind, 'passengers': value}
                          for (route, a, b, day, hour, kind), value in sorted(counts.items())]}
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    with open(output, 'w', encoding='utf-8') as handle:
        json.dump(result, handle)
    return result
