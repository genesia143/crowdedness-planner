import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    'diagnose_schedule_gaps', Path(__file__).resolve().parents[1] / 'scripts' / 'diagnose_schedule_gaps.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TestScheduleGapDiagnostic(unittest.TestCase):
    def test_classifies_cells_and_passenger_segments(self):
        data = {'training_start': '2026-10-22', 'training_end': '2026-10-22',
                'records': [dict(route='r', from_stop_id='a', to_stop_id='b',
                                 date='2026-10-22', hour=h, day_type='weekday', passengers=p)
                            for h, p in [(8, 2), (9, 3), (12, 4)]]}
        schedule = {('r', 'a', 'b', '2026-10-22', 8, 'weekday'): 1}
        result = module.diagnose(data, schedule)
        self.assertEqual(result['same_hour']['cells'], 1)
        self.assertEqual(result['previous_hour_only']['sample_passenger_segment_records'], 3)
        self.assertEqual(result['other_hour_same_day']['sample_passenger_segment_records'], 4)

    def test_rejects_final_week(self):
        with self.assertRaises(ValueError):
            module.diagnose({'training_start': '2026-10-25', 'training_end': '2026-10-25'}, {})
