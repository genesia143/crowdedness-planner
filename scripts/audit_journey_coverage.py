"""Audit returned journey-label coverage using reproducible random GTFS stop pairs.

This reads stops only, never tickets. It samples stop locations, not passenger demand.
Run with the mapped API and OTP already running; outputs contain no ticket records.
"""
import argparse
import csv
import json
import math
import random
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path


def cases(gtfs, seed):
    rng = random.Random(seed)
    with (Path(gtfs) / 'stops.txt').open(encoding='utf-8-sig', newline='') as source:
        stops = []
        for row in csv.DictReader(source):
            try:
                lat, lon = float(row['stop_lat']), float(row['stop_lon'])
            except (KeyError, ValueError):
                continue
            # Broad Delhi bounding box, not a municipal-boundary polygon.
            if 28.4 <= lat <= 28.9 and 76.85 <= lon <= 77.4:
                stops.append((row['stop_id'], row['stop_name'], lat, lon))
    # Balance the seven days and four time periods, then randomise allocation.
    slots = [(d, h) for d in range(7) for h in range(4)]
    slots = (slots * 8)[:200]
    rng.shuffle(slots)
    result = []
    for index, (day, slot) in enumerate(slots, 1):
        while True:
            a, b = rng.sample(stops, 2)
            # Avoid trivial walking-only trips and duplicates at the same coordinates.
            distance = 111 * math.hypot(a[2] - b[2], (a[3] - b[3]) * math.cos(math.radians((a[2] + b[2]) / 2)))
            if distance >= 2:
                break
        hour = 6 + slot * 4 + rng.randrange(4)
        minute = rng.choice([0, 15, 30, 45])
        when = (date(2026, 11, 2) + timedelta(days=day)).isoformat()
        result.append({'case': index, 'origin': a, 'destination': b,
                       'departure': f'{when}T{hour:02d}:{minute:02d}:00+05:30',
                       'day': (date(2026, 11, 2) + timedelta(days=day)).strftime('%A'),
                       'time_band': f'{6 + slot * 4:02d}:00–{10 + slot * 4:02d}:00',
                       'straight_line_km': round(distance, 2)})
    return result


def run_one(case, endpoint):
    a, b = case['origin'], case['destination']
    params = {'from_lat': a[2], 'from_lon': a[3], 'to_lat': b[2], 'to_lon': b[3],
              'departure': case['departure'], 'max_transfer_walk': 1000, 'extra_minutes': 20}
    try:
        with urllib.request.urlopen(endpoint + '/journeys/mapped?' + urllib.parse.urlencode(params), timeout=180) as response:
            body = json.load(response)
        all_journeys = body.get('journeys', [])
        eligible = (body.get('choices') or {}).get('eligible_indices', [])
        entries = []
        for i, journey in enumerate(all_journeys):
            s = journey.get('crowding_summary') or {}
            entries.append({'index': i, 'eligible': i in eligible, 'status': s.get('status'),
                            'journey_pressure': journey.get('journey_pressure'),
                            'labelled_segments': s.get('labelled_segments', 0),
                            'segments_without_label': s.get('segments_without_label', 0),
                            'bus_legs_without_segment_details': s.get('bus_legs_without_segment_details', 0),
                            'broader_window_segments': s.get('broader_window_segments', 0)})
        return {**case, 'routing_source': body.get('routing_source'), 'search_coverage': body.get('search_coverage'),
                'journeys': entries, 'eligible_indices': eligible}
    except (OSError, ValueError, urllib.error.HTTPError) as exc:
        return {**case, 'error': str(exc)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--gtfs', required=True)
    parser.add_argument('--endpoint', default='http://127.0.0.1:8773')
    parser.add_argument('--seed', type=int, default=20261124)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    inputs = cases(args.gtfs, args.seed)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = []
        for item in pool.map(lambda case: run_one(case, args.endpoint), inputs):
            results.append(item)
            if len(results) % 10 == 0:
                print(f'{len(results)}/200 cases complete', flush=True)
    output = {'seed': args.seed, 'design': 'random GTFS stop pairs, Delhi bounding box, >=2 km apart; balanced weekdays and 4-hour bands from 06:00 to 22:00 IST; 2–8 Nov 2026', 'cases': results}
    Path(args.output).write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Wrote', args.output, flush=True)


if __name__ == '__main__':
    main()
