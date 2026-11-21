"""Compact descriptive baseline and its query logic; not a crowding model."""
import json
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def create_database(source, destination, gtfs=None):
    with open(source, encoding='utf-8') as handle:
        data = json.load(handle)
    from service import scheduled_crossings
    scheduled = scheduled_crossings(gtfs, data['training_start'], data['training_end']) if gtfs else None
    db = sqlite3.connect(destination)
    try:
        db.execute('DROP TABLE IF EXISTS signals')
        db.execute('DROP TABLE IF EXISTS metadata')
        db.execute('DROP TABLE IF EXISTS service_signals')
        db.execute('DROP TABLE IF EXISTS scheduled_totals')
        db.execute('CREATE TABLE signals (route TEXT, origin TEXT, destination TEXT, hour INTEGER, day_type TEXT, observed_days INTEGER, total INTEGER, PRIMARY KEY(route,origin,destination,hour,day_type))')
        db.execute('CREATE TABLE service_signals (route TEXT, origin TEXT, destination TEXT, hour INTEGER, day_type TEXT, matched_days INTEGER, sampled_passengers INTEGER, scheduled_crossings INTEGER, unmatched_days INTEGER, PRIMARY KEY(route,origin,destination,hour,day_type))')
        db.execute('CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT)')
        db.execute('CREATE TABLE scheduled_totals (route TEXT, origin TEXT, destination TEXT, hour INTEGER, day_type TEXT, scheduled_days INTEGER, scheduled_crossings INTEGER, PRIMARY KEY(route,origin,destination,hour,day_type))')
        schedule_totals = defaultdict(lambda: [0, 0])
        if scheduled is not None:
            for (route, origin, dest, day, hour, kind), buses in scheduled.items():
                entry = schedule_totals[(route, origin, dest, hour, kind)]
                entry[0] += 1
                entry[1] += buses
        db.executemany('INSERT INTO scheduled_totals VALUES (?,?,?,?,?,?,?)', (key + tuple(value) for key, value in schedule_totals.items()))
        summaries = defaultdict(lambda: [0, 0])
        service_summaries = defaultdict(lambda: [0, 0, 0, 0])
        for row in data['records']:
            key = (row['route'], row['from_stop_id'], row['to_stop_id'], row['hour'], row['day_type'])
            summaries[key][0] += 1
            summaries[key][1] += row['passengers']
            if scheduled is not None:
                day_key = (row['route'], row['from_stop_id'], row['to_stop_id'], row['date'], row['hour'], row['day_type'])
                buses = scheduled.get(day_key, 0)
                values = service_summaries[key]
                if buses:
                    values[0] += 1
                    values[1] += row['passengers']
                    values[2] += buses
                else:
                    values[3] += 1
        db.executemany('INSERT INTO signals VALUES (?,?,?,?,?,?,?)', (key + tuple(value) for key, value in summaries.items()))
        db.executemany('INSERT INTO service_signals VALUES (?,?,?,?,?,?,?,?,?)', (key + tuple(value) for key, value in service_summaries.items()))
        db.executemany('INSERT INTO metadata VALUES (?,?)', [(key, json.dumps(data[key])) for key in ('training_start','training_end','definition','quality')])
        db.commit()
    finally:
        db.close()


def query(database, route, origin, destination, departure):
    from model import normalize, parse_timestamp
    timestamp = parse_timestamp(departure)
    if timestamp.utcoffset() is None:
        raise ValueError('departure must include a timezone offset')
    from datetime import timedelta, timezone
    timestamp = timestamp.astimezone(timezone(timedelta(hours=5, minutes=30)))
    kind = 'weekend' if timestamp.weekday() >= 5 else 'weekday'
    if not Path(database).is_file():
        raise FileNotFoundError('model database not found')
    with sqlite3.connect('file:' + str(Path(database).resolve()) + '?mode=ro', uri=True) as db:
        row = db.execute('SELECT observed_days,total FROM signals WHERE route=? AND origin=? AND destination=? AND hour=? AND day_type=?', (normalize(route),origin,destination,timestamp.hour,kind)).fetchone()
        service = db.execute('SELECT matched_days,sampled_passengers,scheduled_crossings,unmatched_days FROM service_signals WHERE route=? AND origin=? AND destination=? AND hour=? AND day_type=?', (normalize(route),origin,destination,timestamp.hour,kind)).fetchone()
        has_totals = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='scheduled_totals'").fetchone()
        totals = db.execute('SELECT scheduled_days,scheduled_crossings FROM scheduled_totals WHERE route=? AND origin=? AND destination=? AND hour=? AND day_type=?', (normalize(route),origin,destination,timestamp.hour,kind)).fetchone() if has_totals else None
        metadata = {key: json.loads(value) for key, value in db.execute('SELECT key,value FROM metadata')}
    if row is None:
        assumed = None
        if totals and totals[1]:
            assumed = {'sample_passengers_per_scheduled_crossing': 0.0, 'sample_passengers': 0, 'scheduled_days': totals[0], 'scheduled_crossings': totals[1], 'observed_days_with_schedule': 0, 'assumption': 'Zero matched ticket records on scheduled days; valid as a sample count only if ticket ingestion was complete, and not evidence of zero actual riders.'}
        return {'status': 'unavailable', 'reason': 'no matched sample observations for this segment and time', 'all_scheduled_days_proxy': assumed, 'training': metadata}
    days, total = row
    normalized = None
    if service and service[2]:
        normalized = {'sample_passengers_per_scheduled_crossing': service[1] / service[2], 'matched_days': service[0], 'sample_passengers': service[1], 'scheduled_crossings': service[2], 'days_without_matching_schedule': service[3], 'limitation': 'Only days with matched ticket observations and scheduled crossings. Timing depends on the training method; scheduled service may differ from actual service.'}
    all_days = None
    if service and totals and totals[1]:
        all_days = {'sample_passengers_per_scheduled_crossing': service[1] / totals[1], 'sample_passengers': service[1], 'scheduled_days': totals[0], 'scheduled_crossings': totals[1], 'observed_days_with_schedule': service[0], 'days_without_matching_schedule': service[3], 'assumption': 'Days with scheduled service but no matched ticket observations are counted as zero observed tickets; incomplete ticket coverage can bias this value.'}
    return {'status': 'available', 'scheduled_service_proxy': normalized, 'all_scheduled_days_proxy': all_days, 'sample_passengers_per_observed_day': total / days, 'observed_days': days,
            'definition': 'Mean ticket-sample passenger crossings on days with at least one matched ticket. Not occupancy or per-bus load. Timing: ' + metadata['definition'],
            'day_type': kind, 'hour_ist': timestamp.hour, 'training': metadata}
