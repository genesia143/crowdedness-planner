import unittest
from scripts.route_gap_coverage import calculate

class RouteGapCoverageTest(unittest.TestCase):
    def test_route_totals_and_holdout_guard(self):
        base={'route':'8up','from_stop_id':'a','to_stop_id':'b','date':'2026-10-22','hour':8,'day_type':'weekday','passengers':3}
        data={'training_start':'2026-10-22','training_end':'2026-10-22','records':[base,{**base,'hour':9,'passengers':1}]}
        schedule={('8up','a','b','2026-10-22',8,'weekday'):1}
        result=calculate(data,schedule)['8up']
        self.assertEqual(result['sample_passenger_segments'],4)
        self.assertEqual(result['without_same_hour_service'],1)
        self.assertEqual(result['sample_weight_gap_rate'],0.25)
        data['training_end']='2026-10-25'
        with self.assertRaises(ValueError):calculate(data,schedule)

if __name__=='__main__':unittest.main()
