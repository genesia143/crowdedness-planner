import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from scripts.measure_label_coverage import measure

class CoverageTest(unittest.TestCase):
    def test_counts_weight_and_rejects_final_week(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);db=sqlite3.connect(p/'model.db')
            db.execute('CREATE TABLE metadata (key TEXT,value TEXT)')
            db.execute('INSERT INTO metadata VALUES (?,?)', ('day_type_scheme', json.dumps('weekday_saturday_sunday_v1')))
            db.execute('INSERT INTO metadata VALUES (?,?)',('training_end',json.dumps('2026-10-21')))
            db.execute('CREATE TABLE service_signals (route,origin,destination,day_type,hour,matched_days,sampled_passengers)')
            db.execute('CREATE TABLE scheduled_totals (route,origin,destination,day_type,hour,scheduled_days,scheduled_crossings)')
            for hour,value in [(8,10),(9,20),(10,30)]:
                db.execute('INSERT INTO service_signals VALUES (?,?,?,?,?,?,?)',('8UP','a','b','weekday',hour,3,value))
                db.execute('INSERT INTO scheduled_totals VALUES (?,?,?,?,?,?,?)',('8UP','a','b','weekday',hour,4,10))
            db.commit();db.close()
            row={'route':'8UP','from_stop_id':'a','to_stop_id':'b','day_type':'weekday','hour':8,'date':'2026-10-22','passengers':3}
            data={'training_start':'2026-10-22','training_end':'2026-10-22','records':[row,{**row,'hour':11,'passengers':1}]}
            path=p/'data.json';path.write_text(json.dumps(data))
            result=measure(p/'model.db',path)
            self.assertEqual(result['sample_passenger_segment_coverage'],0.75)
            data['training_end']='2026-10-25';path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):measure(p/'model.db',path)

if __name__=='__main__':unittest.main()
