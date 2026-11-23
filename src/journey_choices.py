"""Select time-feasible options without claiming uncalibrated comfort rankings."""
from datetime import datetime, timedelta, timezone
import math


def _timestamp(value):
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (AttributeError, ValueError, TypeError):
        raise ValueError('latest_arrival and journey times must be ISO timestamps')
    if dt.utcoffset() is None:
        raise ValueError('latest_arrival and journey times must include a timezone offset')
    return dt


def _comparable_profile(journey):
    """Return complete strict within-segment percentiles, or None.

    Profiles are comparable only when route, ordered segments and day type
    match. Percentiles are relative sample patterns, not physical comfort.
    """
    from model import day_type, normalize
    profile = []
    for leg in journey.get('legs', []):
        if leg.get('mode') != 'BUS':
            continue
        route = normalize((leg.get('route') or {}).get('shortName'))
        signals = leg.get('v1_signals') or []
        if not route or not signals:
            return None
        for signal in signals:
            comparison = signal.get('relative_crowding') or {}
            if signal.get('status') != 'available' or comparison.get('evidence_tier') == 'broader_window':
                return None
            score = comparison.get('relative_percentile')
            if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 1:
                return None
            start, end = signal.get('from_stop_id'), signal.get('to_stop_id')
            if not start or not end:
                return None
            try:
                moment = _timestamp(signal.get('model_lookup_time')).astimezone(timezone(timedelta(hours=5, minutes=30)))
            except ValueError:
                return None
            profile.append(((route, start, end, day_type(moment)), float(score)))
    return profile or None


def select_choices(journeys, extra_minutes=20, latest_arrival=None):
    try:
        extra = float(extra_minutes)
    except (TypeError, ValueError):
        raise ValueError('extra_minutes must be between 0 and 180')
    if not math.isfinite(extra) or not 0 <= extra <= 180:
        raise ValueError('extra_minutes must be between 0 and 180')
    deadline = _timestamp(latest_arrival) if latest_arrival else None
    valid = []
    for index, journey in enumerate(journeys):
        try:
            end = _timestamp(journey.get('end'))
        except ValueError:
            continue
        if deadline is None or end <= deadline:
            valid.append((end, index))
    if not valid:
        return {'fastest_index': None, 'eligible_indices': [], 'comfortable_index': None,
                'comfort_status': 'No comparable comfort estimate available', 'extra_minutes': extra}
    valid.sort()
    fastest, index = valid[0]
    eligible = [i for end, i in valid if end <= fastest + timedelta(minutes=extra)]
    baseline = _comparable_profile(journeys[index])
    alternatives = []
    if baseline:
        signature = [key for key, _ in baseline]
        baseline_scores = [score for _, score in baseline]
        for candidate in eligible:
            if candidate == index:
                continue
            profile = _comparable_profile(journeys[candidate])
            if not profile or [key for key, _ in profile] != signature:
                continue
            scores = [score for _, score in profile]
            if all(a <= b for a, b in zip(scores, baseline_scores)) and any(a < b for a, b in zip(scores, baseline_scores)):
                alternatives.append((sum(scores) / len(scores), candidate))
    quieter = min(alternatives)[1] if alternatives else None
    return {'fastest_index': index, 'eligible_indices': eligible, 'comfortable_index': None,
            'potentially_quieter_index': quieter,
            'quieter_basis': 'Provisional ticket patterns at different times on the same route and stretches; not measured comfort or seat availability.' if quieter is not None else None,
            'comfort_status': 'Cross-route comfort cannot yet be compared from this ticket sample',
            'extra_minutes': extra, 'basis': 'Scheduled arrival among returned candidates; the selected arrival window includes waiting, walking and riding. Routing may omit suitable options.'}
