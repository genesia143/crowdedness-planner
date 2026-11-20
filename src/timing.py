"""Estimate time from a boarding stop to later segments from GTFS schedules."""
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from statistics import median
from model import normalize, rows


def seconds(value):
    pieces = value.split(':')
    if len(pieces) != 3:
        return None
    try:
        hours, minutes, secs = map(int, pieces)
    except ValueError:
        return None
    if hours < 0 or not 0 <= minutes < 60 or not 0 <= secs < 60:
        return None
    return hours * 3600 + minutes * 60 + secs


class ScheduleOffsets:
    def __init__(self, gtfs):
        gtfs = Path(gtfs)
        routes = {r['route_id']: normalize(r['route_short_name']) for r in rows(gtfs / 'routes.txt')}
        trips = {r['trip_id']: routes.get(r['route_id']) for r in rows(gtfs / 'trips.txt')}
        grouped = defaultdict(list)
        for row in rows(gtfs / 'stop_times.txt'):
            if row['trip_id'] in trips:
                grouped[row['trip_id']].append((int(row['stop_sequence']), row['stop_id'], seconds(row['departure_time'])))
        self.by_start = defaultdict(list)
        for trip, seq in grouped.items():
            route = trips[trip]
            if not route:
                continue
            seq.sort()
            sequence = tuple((stop, time) for _, stop, time in seq)
            for i, (_, stop, time) in enumerate(seq[:-1]):
                if time is not None:
                    self.by_start[(route, stop)].append((sequence, i))

    @lru_cache(maxsize=200000)
    def offsets(self, route, segments):
        if not segments:
            return None
        expected = (segments[0][0],) + tuple(b for _, b in segments)
        values = [[] for _ in segments]
        for complete, offset in self.by_start.get((normalize(route), expected[0]), ()):
            sequence = complete[offset:offset + len(expected)]
            if tuple(stop for stop, _ in sequence) != expected:
                continue
            start = sequence[0][1]
            times = [item[1] for item in sequence[:len(segments)]]
            if any(t is None or t < start for t in times):
                continue
            for index, time in enumerate(times):
                values[index].append(time - start)
        if not values[0]:
            return None
        return tuple(int(median(v)) for v in values)
