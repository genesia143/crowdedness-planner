"""Guarded retrospective ticket-sample evaluation for exactly Oct 25–31.

Run only after the model and evaluation policy have been explicitly frozen.
This is not an estimate of actual bus occupancy. The input is an already
matched model-format JSON artifact, not the original ticket file.
"""
import argparse
from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from service import scheduled_crossings
from model import day_type
from predict import relative_band
from freeze_manifest import fingerprint, verify
from validate_v1_ranking import compare_group

START, END = '2026-10-25', '2026-10-31'
SOURCE_DIR = Path(__file__).resolve().parents[1] / 'src'


def checked_source(path):
    """Fingerprint the source actually imported by this evaluator."""
    if Path(path).resolve() != SOURCE_DIR.resolve():
        raise ValueError('--source must name this checkout\'s src directory')
    return str(SOURCE_DIR)


def subgroup(day):
    weekday = date.fromisoformat(day).weekday()
    return 'saturday' if weekday == 5 else 'sunday' if weekday == 6 else 'weekday'


def bands(rates):
    """Same midrank labels as the tuning diagnostic; ties share a rank."""
    if len(rates) < 3 or len(set(rates.values())) < 2:
        return {}
    labels = {}
    for hour, value in rates.items():
        rank = (sum(v < value for v in rates.values()) +
                .5 * sum(v == value for v in rates.values())) / len(rates)
        labels[hour] = ('likely quieter' if rank < 1 / 3 else
                        'likely busier' if rank > 2 / 3 else 'typical')
    return labels


def evaluate(database, validation, gtfs):
    with sqlite3.connect('file:' + str(Path(database).resolve()) + '?mode=ro', uri=True) as db:
        meta = {key: json.loads(value) for key, value in db.execute('SELECT key,value FROM metadata')}
        if meta['training_start'] != '2026-10-01' or meta['training_end'] != '2026-10-21':
            raise ValueError('expected frozen October 1–21 training model')
        if meta.get('day_type_scheme') != 'weekday_saturday_sunday_v1':
            raise ValueError('final evaluation requires a separate Saturday/Sunday model')
        if 'grouped by ticket boarding hour' not in meta.get('definition', ''):
            raise ValueError('this evaluator requires a boarding-hour model')
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='sunday_observation_days'").fetchone():
            raise ValueError('Sunday broader-window policy requires a rebuilt observation-day index')
        predictions = {}
        sql = '''SELECT t.route,t.origin,t.destination,t.hour,t.day_type,
                        COALESCE(s.sampled_passengers,0),t.scheduled_crossings,
                        COALESCE(s.matched_days,0),t.scheduled_days
                 FROM scheduled_totals t LEFT JOIN service_signals s
                 USING(route,origin,destination,hour,day_type)
                 WHERE t.scheduled_crossings > 0'''
        for route, origin, dest, hour, kind, passengers, buses, days, scheduled_days in db.execute(sql):
            rate = passengers / buses
            predictions[(route, origin, dest, hour, kind)] = rate
    with open(validation, encoding='utf-8') as handle:
        data = json.load(handle)
    if (data['training_start'], data['training_end']) != (START, END):
        raise ValueError('final evaluation input must declare exactly October 25–31')
    if 'grouped by ticket boarding hour' not in data.get('definition', ''):
        raise ValueError('final evaluation target must use the boarding-hour convention')
    observations = defaultdict(int)
    for row in data['records']:
        if not START <= row['date'] <= END:
            raise ValueError('record outside final evaluation dates')
        if row['day_type'] != day_type(date.fromisoformat(row['date'])):
            raise ValueError('final evaluation day type does not match its date')
        key = (row['route'], row['from_stop_id'], row['to_stop_id'], row['date'], row['hour'], row['day_type'])
        observations[key] += row['passengers']
    schedule = scheduled_crossings(gtfs, START, END)
    # Evaluate the exact function serving the API, including any broader-window
    # fallback. Do not reconstruct its evidence rules in this evaluator.
    requested = {(route, origin, dest, kind, hour)
                 for route, origin, dest, day, hour, kind in schedule}
    supported, predictions_by_label, tiers = defaultdict(dict), {}, {}
    with sqlite3.connect('file:' + str(Path(database).resolve()) + '?mode=ro', uri=True) as db:
        for route, origin, dest, kind, hour in requested:
            band = relative_band(db, route, origin, dest, kind, hour)
            label = band.get('label')
            if label not in ('likely quieter', 'typical', 'likely busier'):
                continue
            cell = (route, origin, dest, kind, hour)
            tier = band.get('evidence_tier', 'strict')
            if tier not in ('strict', 'broader_window'):
                raise ValueError(f'Unknown evidence tier: {tier}')
            if 'relative_percentile' not in band:
                raise ValueError('A label must include its production percentile')
            supported[cell[:4]][hour] = band['relative_percentile']
            predictions_by_label[cell] = label
            tiers[cell] = tier
    stats = defaultdict(Counter)
    totals = defaultdict(lambda: [0, 0])
    for (route, origin, dest, day, hour, kind), buses in schedule.items():
        cell = (route, origin, dest, day, hour, kind)
        sample = observations.get(cell, 0)
        group = (route, origin, dest, kind)
        name = subgroup(day)
        stats[name]['scheduled_cells'] += 1
        stats[name]['matched_cells'] += bool(sample)
        stats[name]['sample_passenger_segments'] += sample
        if hour in supported.get(group, {}):
            stats[name]['labelled_sample_passenger_segments'] += sample
            stats[name][tiers[group + (hour,)] + '_labelled_sample_passenger_segments'] += sample
            stats[name][tiers[group + (hour,)] + '_labelled_scheduled_cells'] += 1
        else:
            stats[name]['unlabelled_scheduled_cells'] += 1
        predicted = predictions.get((route, origin, dest, hour, kind))
        if predicted is not None:
            stats[name]['prediction_cells'] += 1
            stats[name]['absolute_error_sum'] += abs(predicted - sample / buses)
        if hour in supported.get(group, {}):
            cell_total = totals[(name, group, hour)]
            cell_total[0] += sample
            cell_total[1] += buses
    for cell, sample in observations.items():
        if cell not in schedule:
            stats[subgroup(cell[3])]['unscheduled_sample_passenger_segments'] += sample
    rankings = defaultdict(Counter)
    labels = defaultdict(Counter)
    for group, hours in supported.items():
        if len(hours) < 3 or len(set(hours.values())) < 2:
            continue
        for name in ('weekday', 'saturday', 'sunday'):
            target = {h: totals[(name, group, h)][0] / totals[(name, group, h)][1]
                      for h in hours if (name, group, h) in totals and totals[(name, group, h)][1]}
            # Different tiers use different reference windows; percentiles
            # between tiers cannot be treated as a common numerical scale.
            group_tiers = {tiers[group + (h,)] for h in target}
            if len(target) >= 2 and len(group_tiers) == 1:
                rankings[name]['evaluated_groups'] += 1
                rankings[name].update(compare_group(hours, target))
            elif len(group_tiers) > 1:
                rankings[name]['mixed_tier_groups_excluded'] += 1
            counts = labels[name]
            counts['training_supported_groups'] += 1
            counts['training_supported_hours'] += len(hours)
            target_bands = bands(target)
            if not target_bands:
                counts['common_hours_excluded_no_target_rank'] += len(target)
                continue
            counts['evaluated_groups'] += 1
            for hour, observed_label in target_bands.items():
                predicted_label = predictions_by_label[group + (hour,)]
                counts['prediction=' + predicted_label + '|target=' + observed_label] += 1
                counts['evaluated_hours'] += 1
                counts['agreement'] += predicted_label == observed_label
                tier = tiers[group + (hour,)]
                counts[tier + '_evaluated_hours'] += 1
                counts[tier + '_agreement'] += predicted_label == observed_label
    result = {}
    for name in ('weekday', 'saturday', 'sunday'):
        row = stats[name]
        count = row['prediction_cells']
        ranking = rankings[name]
        decisive = ranking['concordant'] + ranking['discordant']
        label_counts = labels[name]
        all_matched = row['sample_passenger_segments'] + row['unscheduled_sample_passenger_segments']
        result[name] = {**row, 'labelled_sample_passenger_segment_coverage': row['labelled_sample_passenger_segments'] / row['sample_passenger_segments'] if row['sample_passenger_segments'] else None, 'mean_absolute_error_per_crossing': row['absolute_error_sum'] / count if count else None,
                        'all_matched_sample_passenger_segments': all_matched,
                        'labelled_all_matched_sample_passenger_segment_coverage': row['labelled_sample_passenger_segments'] / all_matched if all_matched else None,
                        'label_agreement': {**label_counts, 'agreement_rate': label_counts['agreement'] / label_counts['evaluated_hours'] if label_counts['evaluated_hours'] else None},
                        'rankings': {**ranking, 'decisive_pairs': decisive,
                                     'concordance': ranking['concordant'] / decisive if decisive else None}}
    return {'start': START, 'end': END, 'matching_quality': data['quality'], 'subgroups': result,
            'unmatched_to_schedule_records': sum(key not in schedule for key in observations),
            'limitations': 'Ticket sample, not occupancy; scheduled zero samples assume complete ingestion. '
                           'Ranking comparisons are correlated and exclude groups mixing evidence tiers. Saturday and Sunday are separate categories. '
                           'Mean absolute error evaluates the original hourly numerical proxy, not the broader-window labels. '
                           'Timing, matching and service differences can bias results. Label coverage is matched, scheduled passenger-segments, not unique people, tickets or complete journeys. '
                           'Label agreement compares training labels against within-subgroup ticket-sample ranks on available supported hours, not actual occupancy; tied rates receive midranks.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('database', 'validation', 'gtfs', 'mapping', 'training-records', 'source', 'manifest', 'output'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--confirm-final-evaluation', action='store_true')
    args = parser.parse_args()
    if not args.confirm_final_evaluation:
        parser.error('model freeze and explicit --confirm-final-evaluation are required')
    inputs = {'database': args.database, 'gtfs': args.gtfs, 'mapping': args.mapping, 'training_records': args.training_records,
              'source': checked_source(args.source), 'evaluator': __file__,
              'ranking': str(Path(__file__).with_name('validate_v1_ranking.py')),
              'manifest_tool': str(Path(__file__).with_name('freeze_manifest.py'))}
    if not verify(args.manifest, inputs):
        raise ValueError('snapshot mismatch; final data was not read')
    if Path(args.output).exists():
        raise FileExistsError('refusing to overwrite a report')
    target_fingerprint = fingerprint(args.validation)
    report = evaluate(args.database, args.validation, args.gtfs)
    if fingerprint(args.validation) != target_fingerprint:
        raise ValueError('evaluation target changed during evaluation; no report written')
    report['evaluation_target_fingerprint'] = target_fingerprint
    if not verify(args.manifest, inputs):
        raise ValueError('snapshot changed during evaluation; no report written')
    with Path(args.output).open('x', encoding='utf-8') as handle:
        json.dump(report, handle, indent=2)
        handle.write('\n')


if __name__ == '__main__':
    main()
