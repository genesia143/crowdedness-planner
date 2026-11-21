import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from model import build


def write(path, fields, records):
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


class PipelineTests(unittest.TestCase):
    def test_dates_passengers_and_segments(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            write(p/'stops.txt', ['stop_id', 'stop_name'], [{'stop_id': x, 'stop_name': n} for x, n in [('a','Alpha'),('b','Beta'),('c','Gamma')]])
            write(p/'routes.txt', ['route_id','route_short_name'], [{'route_id':'1','route_short_name':'8UP'}])
            write(p/'trips.txt', ['trip_id','route_id'], [{'trip_id':'t','route_id':'1'}])
            write(p/'stop_times.txt', ['trip_id','stop_id','stop_sequence'], [{'trip_id':'t','stop_id':x,'stop_sequence':i} for i,x in enumerate('abc')])
            fields = ['route','start_stop_name','end_stop_name','created_at','passenger_count']
            write(p/'tickets.csv', fields, [
                dict(zip(fields,['8UP','Alpha','Gamma','2026-10-01T00:30:00+05:30','2'])),
                dict(zip(fields,['8UP','Alpha','Gamma','2026-10-25T09:00:00+05:30','10'])),
                dict(zip(fields,['8UP','Gamma','Alpha','2026-10-01T09:00:00+05:30','1'])),
            ])
            result = build(p/'tickets.csv', p, '2026-10-01', '2026-10-21', p/'out.json')
            self.assertEqual(result['quality']['in_period'], 2)
            self.assertEqual(result['quality']['matched'], 1)
            self.assertEqual([(r['from_stop_id'],r['to_stop_id'],r['passengers']) for r in result['records']], [('a','b',2),('b','c',2)])
            self.assertEqual(json.loads((p/'out.json').read_text())['training_end'], '2026-10-21')

    def test_segment_timing_moves_to_later_hour(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            write(p/'stops.txt',['stop_id','stop_name'],[{'stop_id':x,'stop_name':n} for x,n in [('a','Alpha'),('b','Beta'),('c','Gamma')]])
            write(p/'routes.txt',['route_id','route_short_name'],[{'route_id':'1','route_short_name':'8UP'}])
            write(p/'trips.txt',['trip_id','route_id'],[{'trip_id':'t','route_id':'1'}])
            write(p/'stop_times.txt',['trip_id','stop_id','stop_sequence','departure_time'],[{'trip_id':'t','stop_id':x,'stop_sequence':i,'departure_time':time} for i,(x,time) in enumerate([('a','08:45:00'),('b','09:05:00'),('c','09:15:00')])])
            fields=['route','start_stop_name','end_stop_name','created_at','passenger_count']
            write(p/'tickets.csv',fields,[dict(zip(fields,['8UP','Alpha','Gamma','2026-10-01T08:50:00+05:30','2']))])
            result=build(p/'tickets.csv',p,'2026-10-01','2026-10-21',p/'out.json',segment_timing=True)
            self.assertEqual([(r['from_stop_id'],r['hour']) for r in result['records']],[('a',8),('b',9)])

    def test_duplicate_stop_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            write(p/'stops.txt',['stop_id','stop_name'],[{'stop_id':'a','stop_name':'Alpha'},{'stop_id':'a','stop_name':'Other'}])
            from model import route_patterns
            with self.assertRaisesRegex(ValueError,'duplicate GTFS stop_id'):
                route_patterns(p)

if __name__ == '__main__':
    unittest.main()
