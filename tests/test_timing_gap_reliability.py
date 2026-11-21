import unittest
from scripts.timing_gap_reliability import summarize


class TimingGapReliabilityTest(unittest.TestCase):
    def test_thresholds_filter_one_fixed_population(self):
        result = summarize([
            ('weekday', 0.02, 'likely quieter', 'likely quieter'),
            ('weekday', 0.12, 'likely quieter', 'likely busier'),
            ('weekday', 0.30, 'typical', 'likely busier'),
        ], thresholds=(0.05, 0.25, 1.0))['weekday']
        self.assertEqual(result['common_hours'], 3)
        self.assertEqual([r['hours'] for r in result['thresholds']], [1, 2, 3])
        self.assertEqual(result['thresholds'][1]['agreement'], 0.5)
        self.assertEqual(result['thresholds'][1]['opposite_ends'], 0.5)
        self.assertAlmostEqual(result['thresholds'][0]['fraction_of_common_population'], 1 / 3)

    def test_zero_retained_does_not_create_a_rate(self):
        row = summarize([('weekday', .5, 'typical', 'typical')], thresholds=(.1,))['weekday']['thresholds'][0]
        self.assertIsNone(row['agreement'])
        self.assertIsNone(row['opposite_ends'])


if __name__ == '__main__':
    unittest.main()
