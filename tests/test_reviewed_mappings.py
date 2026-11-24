import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from reviewed_mappings import inspect

class ReviewAuditTests(unittest.TestCase):
    @patch('reviewed_mappings.route_patterns')
    def test_csv_enforces_route_and_confirmation(self, patterns):
        patterns.return_value = ({'1':'Alpha Station Terminal', '2':'Elsewhere'}, {'8up':{('1',)}})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'mappings.csv'
            path.write_text('route,ticket_stop_name,used_as,stop_id\n8UP,Alpha,boarding,1\n8UP,Alpha,destination,2\n')
            rows = inspect(path, 'unused', confirmed=True)
            self.assertEqual([r['status'] for r in rows], ['accepted', 'review'])
            self.assertIn('stop_not_on_route', rows[1]['reasons'])
            self.assertEqual(inspect(path, 'unused')[0]['status'], 'review')

    @patch('reviewed_mappings.read_xlsx')
    @patch('reviewed_mappings.route_patterns')
    def test_route_score_and_ambiguous_ids(self, patterns, workbook):
        patterns.return_value = ({'1':'Alpha', '2':'Beta', '3':'Elsewhere'}, {'8up':{('1','2')}})
        workbook.return_value = [
            {'route':'8UP','ticket_stop_name':'Alpha','used_as':'boarding','candidate_gtfs_stop_ids':'1'},
            {'route':'8UP','ticket_stop_name':'Alpha','used_as':'boarding','candidate_gtfs_stop_ids':'3'},
            {'route':'8UP','ticket_stop_name':'Other','used_as':'destination','candidate_gtfs_stop_ids':'2'},
            {'route':'8UP','ticket_stop_name':'Beta','used_as':'destination','candidate_gtfs_stop_ids':'1 | 2'},
        ]
        audit = inspect('unused','unused')
        self.assertTrue(all(r['status']=='review' for r in audit))
        self.assertIn('conflicting_stop_ids', audit[0]['reasons'])
        self.assertIn('stop_not_on_route', audit[1]['reasons'])
        self.assertIn('low_name_similarity', audit[2]['reasons'])
        self.assertIn('missing_or_multiple_stop_ids', audit[3]['reasons'])

    @patch('reviewed_mappings.read_xlsx')
    @patch('reviewed_mappings.route_patterns')
    def test_confirmation_overrides_score_but_not_route(self, patterns, workbook):
        patterns.return_value = ({'1':'Alpha Station Terminal', '2':'Elsewhere'}, {'8up':{('1',)}})
        workbook.return_value = [
            {'route':'8UP','ticket_stop_name':'Alpha','used_as':'boarding','candidate_gtfs_stop_ids':'1'},
            {'route':'8UP','ticket_stop_name':'Alpha','used_as':'destination','candidate_gtfs_stop_ids':'2'},
        ]
        audit = inspect('unused','unused',confirmed=True)
        self.assertEqual(audit[0]['status'],'accepted')
        self.assertIn('low_name_similarity', audit[0]['reasons'])
        self.assertEqual(audit[1]['status'],'review')
        self.assertIn('stop_not_on_route', audit[1]['reasons'])

if __name__ == '__main__': unittest.main()
