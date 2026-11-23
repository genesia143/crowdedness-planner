import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from journey_choices import select_choices

class ChoicesTests(unittest.TestCase):
    def test_arrival_window_includes_boundary_and_sorts(self):
        j=[{'end':'2026-10-22T09:21:00+05:30'}, {'end':'2026-10-22T09:00:00+05:30'}, {'end':'2026-10-22T09:20:00+05:30'}]
        c=select_choices(j,20)
        self.assertEqual(c['fastest_index'],1)
        self.assertEqual(c['eligible_indices'],[1,2])
        self.assertIsNone(c['comfortable_index'])
    def test_deadline_and_offsets(self):
        j=[{'end':'2026-10-22T03:30:00+00:00'}, {'end':'2026-10-22T09:10:00+05:30'}]
        self.assertEqual(select_choices(j,20,'2026-10-22T09:05:00+05:30')['eligible_indices'],[0])
        self.assertEqual(select_choices(j,20,'2026-10-22T08:59:00+05:30')['eligible_indices'],[])
    def test_invalid_limits_and_timezone(self):
        for extra in ('nan',-1,181):
            with self.assertRaises(ValueError):select_choices([],extra)
        with self.assertRaises(ValueError):select_choices([],20,'2026-10-22T09:00:00')
    def test_unknown_arrival_is_not_claimed_feasible(self):
        self.assertEqual(select_choices([{'end':'invalid'}])['eligible_indices'],[])

    def test_same_stretch_at_quieter_time_can_be_suggested(self):
        def journey(end, score, route='8UP', tier=None, status='available'):
            return {'end': end, 'legs': [{'mode': 'BUS', 'route': {'shortName':route}, 'v1_signals': [
                {'status':status, 'from_stop_id':'a', 'to_stop_id':'b',
                 'model_lookup_time':'2026-10-22T08:00:00+05:30',
                 'relative_crowding':{'relative_percentile':score, 'evidence_tier':tier}}]}]}
        first=journey('2026-10-22T09:00:00+05:30',.8)
        better=journey('2026-10-22T09:10:00+05:30',.2)
        self.assertEqual(select_choices([first,better])['potentially_quieter_index'],1)
        self.assertIsNone(select_choices([first,journey('2026-10-22T09:10:00+05:30',.2,route='405UP')])['potentially_quieter_index'])
        self.assertIsNone(select_choices([first,journey('2026-10-22T09:10:00+05:30',.2,tier='broader_window')])['potentially_quieter_index'])
        self.assertIsNone(select_choices([first,journey('2026-10-22T09:10:00+05:30',.2,status='unavailable')])['potentially_quieter_index'])
        self.assertIsNone(select_choices([first,journey('2026-10-22T09:21:00+05:30',.2)])['potentially_quieter_index'])

    def test_different_day_type_is_not_comparable(self):
        def journey(end, date, score):
            return {'end':end,'legs':[{'mode':'BUS','route':{'shortName':'8UP'},'v1_signals':[{'status':'available','from_stop_id':'a','to_stop_id':'b','model_lookup_time':date,'relative_crowding':{'relative_percentile':score}}]}]}
        a=journey('2026-10-23T23:55:00+05:30','2026-10-23T23:00:00+05:30',.8)
        b=journey('2026-10-24T00:05:00+05:30','2026-10-24T00:00:00+05:30',.2)
        self.assertIsNone(select_choices([a,b])['potentially_quieter_index'])

if __name__=='__main__':unittest.main()
