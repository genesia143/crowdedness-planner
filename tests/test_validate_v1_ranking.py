import unittest

from scripts.validate_v1_ranking import compare_group


class RankingValidationTests(unittest.TestCase):
    def test_counts_concordance_discordance_and_target_ties(self):
        result = compare_group({8: 1, 9: 2, 10: 3}, {8: 1, 9: 3, 10: 1})
        self.assertEqual(result['hour_pairs'], 3)
        self.assertEqual(result['concordant'], 1)
        self.assertEqual(result['discordant'], 1)
        self.assertEqual(result['target_ties'], 1)

    def test_training_ties_are_not_treated_as_correct(self):
        result = compare_group({8: 1, 9: 1}, {8: 0, 9: 4})
        self.assertEqual(result['training_ties'], 1)
        self.assertEqual(result['concordant'], 0)
