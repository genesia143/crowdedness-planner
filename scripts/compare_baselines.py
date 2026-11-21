"""Compare two models with the same provisional ticket-derived validation target."""
import argparse
import json
import sqlite3
from pathlib import Path


def compare(v1, v2, validation):
    for path in (v1, v2, validation):
        if not Path(path).is_file(): raise FileNotFoundError(path)
    with open(validation,encoding='utf-8') as handle: data=json.load(handle)
    with sqlite3.connect(':memory:') as db:
        db.execute('ATTACH DATABASE ? AS v1', ('file:'+str(Path(v1).resolve())+'?mode=ro',))
        db.execute('ATTACH DATABASE ? AS v2', ('file:'+str(Path(v2).resolve())+'?mode=ro',))
        for version in ('v1','v2'):
            meta=dict(db.execute('SELECT key,value FROM '+version+'.metadata'))
            if json.loads(meta['training_end']) >= data['training_start']:
                raise ValueError('validation must follow the training period')
        db.execute('CREATE TABLE observed (route TEXT, origin TEXT, destination TEXT, hour INTEGER, day_type TEXT, passengers INTEGER)')
        db.executemany('INSERT INTO observed VALUES (?,?,?,?,?,?)', ((r['route'],r['from_stop_id'],r['to_stop_id'],r['hour'],r['day_type'],r['passengers']) for r in data['records']))
        join=' FROM observed o LEFT JOIN v1.signals a ON (o.route=a.route AND o.origin=a.origin AND o.destination=a.destination AND o.hour=a.hour AND o.day_type=a.day_type) LEFT JOIN v2.signals b ON (o.route=b.route AND o.origin=b.origin AND o.destination=b.destination AND o.hour=b.hour AND o.day_type=b.day_type) '
        all_n, v1_n, v2_n, both = db.execute('SELECT COUNT(*), COUNT(a.total), COUNT(b.total), COUNT(CASE WHEN a.total IS NOT NULL AND b.total IS NOT NULL THEN 1 END)'+join).fetchone()
        row=db.execute('SELECT AVG(ABS(1.0*a.total/a.observed_days-o.passengers)),AVG(ABS(1.0*b.total/b.observed_days-o.passengers))'+join+' WHERE a.total IS NOT NULL AND b.total IS NOT NULL').fetchone()
        return {'validation_start':data['training_start'],'validation_end':data['training_end'], 'validation_ticket_matching':data['quality'], 'observations':all_n,'v1_predictions_available':v1_n,'v2_predictions_available':v2_n,'common_predictions':both,'v1_mean_absolute_error_on_common':row[0],'v2_mean_absolute_error_on_common':row[1], 'target':'V2-matched sample passenger counts for segment, boarding hour and day, only where the V2 sample is positive', 'limitation':'V2 defines the common target; incorrect fuzzy matches can bias it. This is not independently observed crowding, excludes zero-observation days, compares conditional counts rather than per-bus loads, and must not by itself select a winner.'}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('v1','v2','validation','output'):p.add_argument('--'+name,required=True)
    a=p.parse_args(); result=compare(a.v1,a.v2,a.validation)
    Path(a.output).write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result,indent=2))
