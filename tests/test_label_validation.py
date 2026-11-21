import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from validate_v1_labels import bands, compare


class LabelValidationTests(unittest.TestCase):
    def test_midrank_and_insufficient_variation(self):
        self.assertEqual(bands({8: 1, 9: 2, 10: 3}),
                         {8: 'likely quieter', 9: 'typical', 10: 'likely busier'})
        self.assertEqual(bands({8: 1, 9: 1, 10: 1}), {})

    def test_reversed_targets_are_recorded(self):
        counts, excluded = compare({8: 1, 9: 2, 10: 3}, {8: 3, 9: 2, 10: 1})
        self.assertEqual(excluded, 0)
        self.assertEqual(counts[('likely quieter', 'likely busier')], 1)
        self.assertEqual(counts[('likely busier', 'likely quieter')], 1)

    def test_constant_target_is_excluded(self):
        counts, excluded = compare({8: 1, 9: 2, 10: 3}, {8: 0, 9: 0, 10: 0})
        self.assertFalse(counts)
        self.assertEqual(excluded, 3)


if __name__ == '__main__':
    unittest.main()
