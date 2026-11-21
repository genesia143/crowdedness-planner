import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from model import StopMatcher, match_segments, normalize, parse_timestamp

class MatchingTests(unittest.TestCase):
    def setUp(self):
        self.names = {'a': 'Alpha', 'b': 'Beta', 'c': 'Gamma', 'd': 'Delta'}
    def test_counts_only_traversed_segments(self):
        self.assertEqual(match_segments('8UP', 'alpha', 'GAMMA', self.names, {'8up': {('a', 'b', 'c')}}), (('a', 'b'), ('b', 'c')))
    def test_rejects_wrong_direction_and_ambiguous_patterns(self):
        self.assertIsNone(match_segments('8UP', 'Gamma', 'Alpha', self.names, {'8up': {('a', 'b', 'c')}}))
        self.assertIsNone(match_segments('8UP', 'Alpha', 'Gamma', self.names, {'8up': {('a', 'b', 'c'), ('a', 'd', 'c')}}))
    def test_fuzzy_is_route_scoped_and_opt_in(self):
        patterns = {'8up': {('a', 'b', 'c')}, '9up': {('d', 'c')}}
        self.assertIsNone(StopMatcher(self.names, patterns).match('8UP', 'Alphaa', 'Gamma')[0])
        segments, method = StopMatcher(self.names, patterns, fuzzy=True).match('8UP', 'Alphaa', 'Gamma')
        self.assertEqual((segments, method), ((('a', 'b'), ('b', 'c')), 'fuzzy'))
        self.assertIsNone(StopMatcher(self.names, patterns, fuzzy=True).match('9UP', 'Alphaa', 'Gamma')[0])
    def test_ambiguous_fuzzy_names_are_rejected(self):
        names = {'a': 'Central Park North', 'b': 'Central Park South', 'c': 'Gamma'}
        matcher = StopMatcher(names, {'8up': {('a', 'b', 'c')}}, fuzzy=True)
        self.assertEqual(matcher.resolve('8up', 'Central Park'), (None, 'unmatched'))
    def test_fuzzy_rejects_direction_and_block_changes(self):
        names = {'a': 'East Patel Nagar', 'b': 'Mangol Puri S Block', 'c': 'Gamma'}
        matcher = StopMatcher(names, {'8up': {('a', 'b', 'c')}}, fuzzy=True)
        self.assertEqual(matcher.resolve('8up', 'West Patel Nagar'), (None, 'ambiguous'))
        self.assertEqual(matcher.resolve('8up', 'Mangol Puri R Block'), (None, 'ambiguous'))
    def test_reviewed_stop_id_uses_route_and_role(self):
        names = {'a':'Alpha', 'b':'Beta', 'c':'Gamma', 'd':'Beta'}
        patterns = {'8up': {('a','b','c'), ('a','d','c')}, '9up': {('a','d','c')}}
        reviewed = {('8up','custom beta','boarding'):'b'}
        matcher = StopMatcher(names, patterns, reviewed=reviewed)
        self.assertEqual(matcher.match('8UP','Custom Beta','Gamma'), ((('b','c'),), 'reviewed'))
        self.assertIsNone(matcher.match('9UP','Custom Beta','Gamma')[0])
        self.assertIsNone(matcher.match('8UP','Alpha','Custom Beta')[0])
    def test_fractional_timestamp_compatibility(self):
        self.assertEqual(parse_timestamp('2026-10-28 10:20:42.89825+05:30').microsecond, 898250)
        self.assertIsNotNone(parse_timestamp('2026-10-28T10:20:42Z').utcoffset())
    def test_normalizes_punctuation(self):
        self.assertEqual(normalize(' 8-UP '), '8 up')

if __name__ == '__main__':
    unittest.main()
