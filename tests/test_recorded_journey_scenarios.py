"""Regression checks on real recorded routes; fixtures are not ground truth."""
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from journey_choices import select_choices

FIXTURES=Path(__file__).resolve().parent/'fixtures'/'otp'/'api'

def load(name):
    data=json.loads((FIXTURES/(name+'.json')).read_text())
    if data['status']!=200:raise AssertionError('recorded API response was not successful')
    return data['body']['journeys']

class RecordedJourneyScenarios(unittest.TestCase):
    def test_place_to_place_includes_access_and_egress_walk(self):
        journeys=load('14_place_to_place')
        with_both=[j for j in journeys if j['legs'][0]['mode']=='WALK' and j['legs'][-1]['mode']=='WALK']
        self.assertTrue(with_both)
        self.assertTrue(all(j['legs'][0]['distance']>0 and j['legs'][-1]['distance']>0 for j in with_both))

    def test_outer_region_has_real_recorded_bus_journey(self):
        journeys=load('13_br_md_thu_0800')
        self.assertTrue(any(any(l['mode']=='BUS' for l in j['legs']) for j in journeys))

    def test_late_service_and_twenty_minute_arrival_window(self):
        journeys=load('02_kg_np_thu_2300')
        result=select_choices(journeys,20)
        self.assertIsNotNone(result['fastest_index'])
        self.assertIn(result['fastest_index'],result['eligible_indices'])
        self.assertIsNone(result['comfortable_index'])

    def test_zero_transfer_limit_case_is_not_misrepresented_as_exclusion(self):
        a=load('09_rg_np_thu_0900')
        b=load('10_rg_np_thu_0900_walk0')
        self.assertEqual(len(a),len(b))

if __name__=='__main__':unittest.main()
