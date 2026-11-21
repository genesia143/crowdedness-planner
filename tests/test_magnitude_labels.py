import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from compare_magnitude_labels import magnitude


class MagnitudeTests(unittest.TestCase):
    def test_flat_variation_remains_typical(self):
        self.assertEqual(set(magnitude({8: 1, 9: 1.05, 10: .95}).values()), {'typical'})

    def test_large_relative_increase_is_busier(self):
        self.assertEqual(magnitude({8: 1, 9: 1, 10: 3})[10], 'likely busier')

    def test_zero_mean_and_insufficient_hours_are_unavailable(self):
        self.assertEqual(magnitude({8: 0, 9: 0, 10: 0}), {})
        self.assertEqual(magnitude({8: 1, 9: 2}), {})


if __name__ == '__main__': unittest.main()
