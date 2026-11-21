import csv
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from service import scheduled_crossings
from predict import create_database, query
import json

def write(p, fields, data):
    with open(p, 'w', newline='') as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(data)

class ServiceTests(unittest.TestCase):
    def test_calendar_exception_and_after_midnight(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            write(p/'routes.txt',['route_id','route_short_name'],[{'route_id':'1','route_short_name':'8UP'}])
            write(p/'trips.txt',['trip_id','route_id','service_id'],[{'trip_id':'t','route_id':'1','service_id':'s'}])
            write(p/'stop_times.txt',['trip_id','stop_id','stop_sequence','departure_time'],[{'trip_id':'t','stop_id':'a','stop_sequence':1,'departure_time':'25:10:00'},{'trip_id':'t','stop_id':'b','stop_sequence':2,'departure_time':'25:15:00'}])
            write(p/'calendar.txt',['service_id','monday','tuesday','wednesday','thursday','friday','saturday','sunday','start_date','end_date'],[{'service_id':'s','monday':1,'tuesday':1,'wednesday':1,'thursday':1,'friday':1,'saturday':1,'sunday':1,'start_date':'20261001','end_date':'20261031'}])
            write(p/'calendar_dates.txt',['service_id','date','exception_type'],[{'service_id':'s','date':'20261001','exception_type':'2'}])
            counts=scheduled_crossings(p,'2026-10-02','2026-10-03')
            self.assertNotIn(('8up','a','b','2026-10-02',1,'weekday'),counts)
            self.assertEqual(counts[('8up','a','b','2026-10-03',1,'weekend')],1)
            records = [{'route':'8up','from_stop_id':'a','to_stop_id':'b','date':'2026-10-03','hour':1,'day_type':'weekend','passengers':4}]
            source = {'training_start':'2026-10-02','training_end':'2026-10-03','definition':'sample','quality':{},'records':records}
            (p/'input.json').write_text(json.dumps(source))
            create_database(p/'input.json', p/'model.db', gtfs=p)
            proxy = query(p/'model.db','8UP','a','b','2026-10-03T01:00:00+05:30')['scheduled_service_proxy']
            self.assertEqual(proxy['sample_passengers_per_scheduled_crossing'], 4)
            self.assertEqual(proxy['scheduled_crossings'], 1)
            all_days = query(p/'model.db','8UP','a','b','2026-10-03T01:00:00+05:30')['all_scheduled_days_proxy']
            self.assertEqual(all_days['sample_passengers_per_scheduled_crossing'], 4)
            self.assertEqual(all_days['scheduled_days'], 1)

    def test_zero_observation_scheduled_day_changes_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            write(p/'routes.txt',['route_id','route_short_name'],[{'route_id':'1','route_short_name':'8UP'}])
            write(p/'trips.txt',['trip_id','route_id','service_id'],[{'trip_id':'t','route_id':'1','service_id':'s'}])
            write(p/'stop_times.txt',['trip_id','stop_id','stop_sequence','departure_time'],[{'trip_id':'t','stop_id':'a','stop_sequence':1,'departure_time':'09:00:00'},{'trip_id':'t','stop_id':'b','stop_sequence':2,'departure_time':'09:05:00'},{'trip_id':'t','stop_id':'c','stop_sequence':3,'departure_time':'09:10:00'}])
            write(p/'calendar.txt',['service_id','monday','tuesday','wednesday','thursday','friday','saturday','sunday','start_date','end_date'],[{'service_id':'s','monday':1,'tuesday':1,'wednesday':1,'thursday':1,'friday':1,'saturday':0,'sunday':0,'start_date':'20261001','end_date':'20261031'}])
            source={'training_start':'2026-10-01','training_end':'2026-10-02','definition':'sample','quality':{},'records':[{'route':'8up','from_stop_id':'a','to_stop_id':'b','date':'2026-10-01','hour':9,'day_type':'weekday','passengers':4}]}
            (p/'input.json').write_text(json.dumps(source)); create_database(p/'input.json',p/'model.db',gtfs=p)
            result=query(p/'model.db','8UP','a','b','2026-10-05T09:00:00+05:30')
            self.assertEqual(result['scheduled_service_proxy']['sample_passengers_per_scheduled_crossing'],4)
            self.assertEqual(result['all_scheduled_days_proxy']['sample_passengers_per_scheduled_crossing'],2)
            self.assertEqual(result['all_scheduled_days_proxy']['scheduled_days'],2)
            missing=query(p/'model.db','8UP','b','c','2026-10-05T09:00:00+05:30')
            self.assertEqual(missing['status'],'unavailable')
            self.assertEqual(missing['all_scheduled_days_proxy']['sample_passengers_per_scheduled_crossing'],0)

if __name__ == '__main__': unittest.main()
