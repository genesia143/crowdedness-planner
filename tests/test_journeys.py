import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'src'))
from journeys import JourneyPlanner
from predict import create_database


def write(path, fields, values):
    with open(path,'w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader(); writer.writerows(values)

class JourneyTests(unittest.TestCase):
    def test_direct_journey_and_no_service(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            write(p/'stops.txt',['stop_id','stop_name'],[{'stop_id':'a','stop_name':'Alpha'},{'stop_id':'b','stop_name':'Beta'},{'stop_id':'c','stop_name':'Gamma'}])
            write(p/'routes.txt',['route_id','route_short_name'],[{'route_id':'r','route_short_name':'8UP'}])
            write(p/'trips.txt',['trip_id','route_id','service_id'],[{'trip_id':'t','route_id':'r','service_id':'s'}])
            write(p/'stop_times.txt',['trip_id','stop_sequence','stop_id','arrival_time','departure_time'],[{'trip_id':'t','stop_sequence':i,'stop_id':s,'arrival_time':time,'departure_time':time} for i,(s,time) in enumerate([('a','09:00:00'),('b','09:10:00'),('c','09:20:00')])])
            write(p/'calendar.txt',['service_id','monday','tuesday','wednesday','thursday','friday','saturday','sunday','start_date','end_date'],[{'service_id':'s','monday':1,'tuesday':1,'wednesday':1,'thursday':1,'friday':1,'saturday':0,'sunday':0,'start_date':'20261001','end_date':'20261031'}])
            data={'training_start':'2026-10-01','training_end':'2026-10-21','definition':'observed ticket-sample passenger journeys crossing a segment, grouped by ticket boarding hour','quality':{},'records':[]}
            (p/'data.json').write_text(json.dumps(data)); create_database(p/'data.json',p/'model.db')
            planner=JourneyPlanner(p,p/'model.db')
            self.assertEqual(planner.search_stops('alpha')[0]['stop_id'],'a')
            result=planner.journeys('a','c','2026-10-22T08:50:00+05:30')
            self.assertEqual(len(result['journeys']),1)
            self.assertEqual(result['journeys'][0]['waiting_minutes'],10)
            self.assertEqual(result['journeys'][0]['ride_minutes'],20)
            self.assertEqual(len(result['journeys'][0]['segments']),2)
            self.assertEqual(result['journeys'][0]['segments'][0]['signal_status'],'unavailable')
            self.assertEqual(planner.journeys('a','c','2026-10-25T08:50:00+05:30')['journeys'],[])
            with self.assertRaises(ValueError):planner.journeys('a','c','2026-10-22T08:50:00')

    def test_one_transfer_and_minimum_wait(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            write(p/'stops.txt',['stop_id','stop_name'],[{'stop_id':x,'stop_name':x.upper()} for x in 'abc'])
            write(p/'routes.txt',['route_id','route_short_name'],[{'route_id':'r1','route_short_name':'1UP'},{'route_id':'r2','route_short_name':'2UP'}])
            write(p/'trips.txt',['trip_id','route_id','service_id'],[{'trip_id':'t1','route_id':'r1','service_id':'s'},{'trip_id':'t2','route_id':'r2','service_id':'s'},{'trip_id':'t3','route_id':'r2','service_id':'s'}])
            times=[('t1','a','09:00:00'),('t1','b','09:10:00'),('t2','b','09:15:00'),('t2','c','09:30:00'),('t3','b','09:14:00'),('t3','c','09:25:00')]
            write(p/'stop_times.txt',['trip_id','stop_sequence','stop_id','arrival_time','departure_time'],[{'trip_id':trip,'stop_sequence':i,'stop_id':stop,'arrival_time':time,'departure_time':time} for i,(trip,stop,time) in enumerate(times)])
            write(p/'calendar.txt',['service_id','monday','tuesday','wednesday','thursday','friday','saturday','sunday','start_date','end_date'],[{'service_id':'s','monday':1,'tuesday':1,'wednesday':1,'thursday':1,'friday':1,'saturday':0,'sunday':0,'start_date':'20261001','end_date':'20261031'}])
            data={'training_start':'2026-10-01','training_end':'2026-10-21','definition':'observed ticket-sample passenger journeys crossing a segment, grouped by ticket boarding hour','quality':{},'records':[]}
            (p/'data.json').write_text(json.dumps(data));create_database(p/'data.json',p/'model.db')
            result=JourneyPlanner(p,p/'model.db').transfer_journeys('a','c','2026-10-22T08:50:00+05:30')
            self.assertEqual(len(result['journeys']),1)
            self.assertEqual(result['journeys'][0]['transfer_wait_minutes'],5)
            self.assertEqual(result['journeys'][0]['legs'][1]['trip_id'],'t2')

if __name__=='__main__': unittest.main()
