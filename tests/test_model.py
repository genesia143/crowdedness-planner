import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from model import match_segments, normalize

class MatchingTests(unittest.TestCase):
    def setUp(self):
        self.names = {'a': 'Alpha', 'b': 'Beta', 'c': 'Gamma', 'd': 'Delta'}
    def test_counts_only_traversed_segments(self):
        self.assertEqual(match_segments('8UP', 'alpha', 'GAMMA', self.names, {'8up': {('a', 'b', 'c')}}), (('a', 'b'), ('b', 'c')))
    def test_rejects_wrong_direction_and_ambiguous_patterns(self):
        self.assertIsNone(match_segments('8UP', 'Gamma', 'Alpha', self.names, {'8up': {('a', 'b', 'c')}}))
        self.assertIsNone(match_segments('8UP', 'Alpha', 'Gamma', self.names, {'8up': {('a', 'b', 'c'), ('a', 'd', 'c')}}))
    def test_normalizes_punctuation(self):
        self.assertEqual(normalize(' 8-UP '), '8 up')

if __name__ == '__main__':
    unittest.main()
