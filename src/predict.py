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
        db.execute('CREATE TABLE signals (route TEXT, origin TEXT, destination TEXT, hour INTEGER, day_type TEXT, observed_days INTEGER, total INTEGER, PRIMARY KEY(route,origin,destination,hour,day_type))')
        db.execute('CREATE TABLE service_signals (route TEXT, origin TEXT, destination TEXT, hour INTEGER, day_type TEXT, matched_days INTEGER, sampled_passengers INTEGER, scheduled_crossings INTEGER, unmatched_days INTEGER, PRIMARY KEY(route,origin,destination,hour,day_type))')
        db.execute('CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT)')
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
        metadata = {key: json.loads(value) for key, value in db.execute('SELECT key,value FROM metadata')}
    if row is None:
        return {'status': 'unavailable', 'reason': 'no matched sample observations for this segment and time', 'training': metadata}
    days, total = row
    normalized = None
    if service and service[2]:
        normalized = {'sample_passengers_per_scheduled_crossing': service[1] / service[2], 'matched_days': service[0], 'sample_passengers': service[1], 'scheduled_crossings': service[2], 'days_without_matching_schedule': service[3], 'limitation': 'Only days with matched ticket observations and scheduled crossings. Timing depends on the training method; scheduled service may differ from actual service.'}
    return {'status': 'available', 'scheduled_service_proxy': normalized, 'sample_passengers_per_observed_day': total / days, 'observed_days': days,
            'definition': 'Mean ticket-sample passenger crossings on days with at least one matched ticket. Not occupancy or per-bus load. Timing: ' + metadata['definition'],
            'day_type': kind, 'hour_ist': timestamp.hour, 'training': metadata}
