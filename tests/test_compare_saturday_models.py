import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.compare_saturday_models import compare

class SaturdayComparisonTests(unittest.TestCase):
    def test_same_cells_and_holdout_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,kind,scheduled in [('pooled','weekend',4),('split','saturday',3)]:
                with sqlite3.connect(root/(name+'.db')) as db:
                    db.executescript('CREATE TABLE metadata(key,value); CREATE TABLE service_signals(route,origin,destination,day_type,hour,matched_days,sampled_passengers); CREATE TABLE scheduled_totals(route,origin,destination,day_type,hour,scheduled_days,scheduled_crossings);')
                    db.execute('INSERT INTO metadata VALUES (?,?)',('training_end','"2026-10-21"'))
                    for hour,value in [(8,10),(9,20),(10,30)]:
                        db.execute('INSERT INTO service_signals VALUES (?,?,?,?,?,?,?)',('r','a','b',kind,hour,3,value))
                        db.execute('INSERT INTO scheduled_totals VALUES (?,?,?,?,?,?,?)',('r','a','b',kind,hour,scheduled,10))
            records=[{'route':'r','from_stop_id':'a','to_stop_id':'b','date':'2026-10-24','hour':hour,'day_type':'saturday','passengers':value} for hour,value in [(8,1),(9,2),(10,3)]]
            data={'training_start':'2026-10-22','training_end':'2026-10-24','records':records};path=root/'data.json';path.write_text(json.dumps(data))
            schedule={('r','a','b','2026-10-24',hour,'saturday'):1 for hour in (8,9,10)}
            with patch('scripts.compare_saturday_models.scheduled_crossings',return_value=schedule):
                result=compare(root/'pooled.db',root/'split.db',path,root)
            self.assertEqual(result['hours'],3);self.assertEqual(result['pooled_agreement'],1);self.assertEqual(result['split_agreement'],1)
            data['training_end']='2026-10-25';path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):compare(root/'pooled.db',root/'split.db',path,root)

if __name__=='__main__':unittest.main()
