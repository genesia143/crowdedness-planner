import csv
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from timing import ScheduleOffsets, seconds

def write(path, fields, records):
    with open(path,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(records)

class TimingTests(unittest.TestCase):
    def test_median_offsets_and_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            write(p/'routes.txt',['route_id','route_short_name'],[{'route_id':'r','route_short_name':'8UP'}])
            write(p/'trips.txt',['trip_id','route_id'],[{'trip_id':'t1','route_id':'r'},{'trip_id':'t2','route_id':'r'}])
            records=[]
            for trip, times in [('t1',['23:50:00','24:00:00','24:15:00']),('t2',['23:50:00','24:10:00','24:20:00'])]:
                records.extend({'trip_id':trip,'stop_sequence':i,'stop_id':stop,'departure_time':time} for i,(stop,time) in enumerate(zip('abc',times)))
            write(p/'stop_times.txt',['trip_id','stop_sequence','stop_id','departure_time'],records)
            offsets=ScheduleOffsets(p)
            self.assertEqual(offsets.offsets('8UP',(('a','b'),('b','c'))),(0,900))
            self.assertIsNone(offsets.offsets('8UP',(('a','c'),)))
            self.assertEqual(seconds('25:10:00'),90600)

if __name__ == '__main__': unittest.main()
