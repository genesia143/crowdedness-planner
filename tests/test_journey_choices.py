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

if __name__=='__main__':unittest.main()
