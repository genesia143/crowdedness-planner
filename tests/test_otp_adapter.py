import sys,unittest,csv,tempfile
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from otp_adapter import transfer_walks_within_limit,gtfs_id,annotate_v1

class AdapterTests(unittest.TestCase):
    def test_transfer_walk_limit(self):
        def leg(mode,distance): return {'mode':mode,'distance':distance}
        self.assertTrue(transfer_walks_within_limit([leg('BUS',0),leg('WALK',600),leg('WALK',400),leg('BUS',0)]))
        self.assertFalse(transfer_walks_within_limit([leg('BUS',0),leg('WALK',1001),leg('BUS',0)]))
        self.assertFalse(transfer_walks_within_limit([leg('BUS',0),leg('WALK',None),leg('BUS',0)]))
        self.assertFalse(transfer_walks_within_limit([leg('BUS',0),leg('WALK',float('nan')),leg('BUS',0)]))
        self.assertFalse(transfer_walks_within_limit([leg('BUS',0),leg('WALK',float('inf')),leg('BUS',0)]))
        self.assertTrue(transfer_walks_within_limit([leg('WALK',2000),leg('BUS',0)]))
    def test_gtfs_prefix(self):
        self.assertEqual(gtfs_id('1:123'),'123')
        self.assertIsNone(gtfs_id('123'))

    def test_each_transfer_is_checked_separately_and_access_walk_is_excluded(self):
        legs = [
            {'mode': 'WALK', 'distance': 1500}, {'mode': 'BUS'},
            {'mode': 'WALK', 'distance': 900}, {'mode': 'BUS'},
            {'mode': 'WALK', 'distance': 950}, {'mode': 'BUS'},
            {'mode': 'WALK', 'distance': 1500},
        ]
        self.assertTrue(transfer_walks_within_limit(legs, 1000))
        legs[4]['distance'] = 1001
        self.assertFalse(transfer_walks_within_limit(legs, 1000))

    @patch('otp_adapter.model_timing_basis', return_value='boarding')
    @patch('otp_adapter.query')
    def test_attaches_only_matching_gtfs_sequence_at_segment_time(self, query, timing_basis):
        query.return_value={'status':'available','all_scheduled_days_proxy':{'sample_passengers':2}}
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            with open(p/'stop_times.txt','w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=['trip_id','stop_sequence','stop_id','departure_time']);w.writeheader()
                for i,(sid,t) in enumerate([('a','09:00:00'),('b','09:10:00'),('c','09:20:00')]):w.writerow({'trip_id':'t','stop_sequence':i,'stop_id':sid,'departure_time':t})
            leg={'mode':'BUS','route':{'shortName':'8UP'},'trip':{'gtfsId':'1:t'},'serviceDate':'2026-10-22','from':{'stop':{'gtfsId':'1:a'}},'to':{'stop':{'gtfsId':'1:c'}},'intermediateStops':[{'gtfsId':'1:b'}]}
            result=annotate_v1({'legs':[leg]},p,'unused')
            self.assertEqual(len(result['legs'][0]['v1_signals']),2)
            self.assertEqual(query.call_args_list[1].args[4],'2026-10-22T09:00:00+05:30')
            query.reset_mock()
            timing_basis.return_value = 'crossing'
            annotate_v1({'legs':[leg]},p,'unused')
            self.assertEqual(query.call_args_list[1].args[4],'2026-10-22T09:10:00+05:30')
            timing_basis.return_value = 'boarding'
            query.reset_mock()
            import copy
            annotate_v1({'legs':[leg,copy.deepcopy(leg)]},p,'unused')
            self.assertEqual(query.call_count,2)
            leg['intermediateStops']=[]
            result=annotate_v1({'legs':[leg]},p,'unused')
            self.assertIn('unavailable',result['legs'][0]['v1_signal_status'])

if __name__=='__main__': unittest.main()
