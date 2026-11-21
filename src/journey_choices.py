"""Select time-feasible options without claiming uncalibrated comfort rankings."""
from datetime import datetime, timedelta
import math


def _timestamp(value):
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (AttributeError, ValueError, TypeError):
        raise ValueError('latest_arrival and journey times must be ISO timestamps')
    if dt.utcoffset() is None:
        raise ValueError('latest_arrival and journey times must include a timezone offset')
    return dt


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
    return {'fastest_index': index, 'eligible_indices': eligible, 'comfortable_index': None,
            'comfort_status': 'Cross-route comfort cannot yet be compared from this ticket sample',
            'extra_minutes': extra, 'basis': 'Scheduled arrival among returned candidates; 20-minute window includes waiting, walking and riding. Routing may omit suitable options.'}
