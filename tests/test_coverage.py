import sys
import unittest
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'src')); sys.path.insert(0,str(root/'scripts'))
from diagnose_coverage import classify
from model import StopMatcher

class CoverageTests(unittest.TestCase):
    def test_disjoint_categories(self):
        m=StopMatcher({'a':'Alpha','b':'Beta','c':'Gamma'}, {'8up':{('a','b','c')}})
        examples=[(('9UP','Alpha','Beta'),'route_unmatched'),(('8UP','Alpha','Beta'),'matched'),(('8UP','',''),'both_stops_unresolved'),(('8UP','','Beta'),'boarding_stop_missing'),(('8UP','Alpha','other'),'destination_stop_unmatched'),(('8UP','Gamma','Alpha'),'path_unmatched_or_ambiguous')]
        for inputs, expected in examples:
            with self.subTest(inputs=inputs): self.assertEqual(classify(m,*inputs),expected)

if __name__=='__main__': unittest.main()
