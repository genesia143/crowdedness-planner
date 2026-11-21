import csv
import sys
import tempfile
import unittest
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'scripts'))
from prepare_stop_review import prepare

def write(path, fields, rows):
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(rows)

class ReviewTests(unittest.TestCase):
    def test_only_training_period_and_prioritizes_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            write(p/'stops.txt',['stop_id','stop_name'],[{'stop_id':'a','stop_name':'Alpha'},{'stop_id':'b','stop_name':'Beta'}])
            write(p/'routes.txt',['route_id','route_short_name'],[{'route_id':'r','route_short_name':'8UP'}])
            write(p/'trips.txt',['trip_id','route_id'],[{'trip_id':'t','route_id':'r'}])
            write(p/'stop_times.txt',['trip_id','stop_id','stop_sequence'],[{'trip_id':'t','stop_id':'a','stop_sequence':1},{'trip_id':'t','stop_id':'b','stop_sequence':2}])
            fields=['route','start_stop_name','end_stop_name','created_at','passenger_count']
            def ticket(name,day): return dict(zip(fields,['8UP',name,'Beta',day+'T08:00:00+05:30','1']))
            write(p/'tickets.csv',fields,[ticket('Alphaa','2026-10-01'),ticket('Alphaa','2026-10-02'),ticket('Alphaa','2026-10-25'),ticket('unknown','2026-10-01')])
            prepare(p/'tickets.csv',p,'2026-10-01','2026-10-21',p/'out.csv')
            with open(p/'out.csv',newline='') as f: results=list(csv.DictReader(f))
            self.assertEqual(results[0]['ticket_stop_name'],'Alphaa')
            self.assertEqual(results[0]['ticket_rows'],'2')
            self.assertEqual(results[0]['candidate_gtfs_stop_ids'],'a')
            self.assertEqual(len(results),2)

if __name__ == '__main__': unittest.main()
