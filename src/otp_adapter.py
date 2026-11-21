"""Helpers for the local OpenTripPlanner trial, not a production router."""
from datetime import date, datetime, timedelta, timezone
from math import isfinite
from model import rows
from predict import query, model_timing_basis


def transfer_walks_within_limit(legs, maximum_metres=1000):
    """Check contiguous walking legs between bus legs; reject unknown distances."""
    if maximum_metres < 0: raise ValueError('maximum distance must not be negative')
    transit=[i for i,leg in enumerate(legs) if leg.get('mode') == 'BUS']
    for first, second in zip(transit,transit[1:]):
        between=legs[first+1:second]
        if not between:
            end_stop = ((legs[first].get('to') or {}).get('stop') or {}).get('gtfsId')
            start_stop = ((legs[second].get('from') or {}).get('stop') or {}).get('gtfsId')
            if not end_stop or not start_stop or end_stop != start_stop:
                return False
        if any(leg.get('mode') != 'WALK' or not isinstance(leg.get('distance'), (int, float)) or not isfinite(leg['distance']) or leg['distance'] < 0 for leg in between):
            return False
        if sum(leg['distance'] for leg in between) > maximum_metres:
            return False
    return True


def gtfs_id(value):
    if not value or ':' not in value: return None
    return value.split(':',1)[1]


def annotate_v1(itinerary, gtfs, database):
    """Attach existing V1 proxies only where OTP and the GTFS trip agree exactly."""
    from pathlib import Path
    gtfs=Path(gtfs)
    legs=itinerary['legs']
    ids={gtfs_id((leg.get('trip') or {}).get('gtfsId')) for leg in legs if leg.get('mode')=='BUS'}
    ids.discard(None)
    times={trip:[] for trip in ids}
    for row in rows(gtfs/'stop_times.txt'):
        if row['trip_id'] in times: times[row['trip_id']].append(row)
    signal_cache = {}
    timing_basis = model_timing_basis(database)
    for leg in legs:
        if leg.get('mode') != 'BUS': continue
        trip=gtfs_id((leg.get('trip') or {}).get('gtfsId'))
        route=(leg.get('route') or {}).get('shortName')
        first=gtfs_id(((leg.get('from') or {}).get('stop') or {}).get('gtfsId'))
        last=gtfs_id(((leg.get('to') or {}).get('stop') or {}).get('gtfsId'))
        middle=[gtfs_id(x.get('gtfsId')) for x in (leg.get('intermediateStops') or [])]
        target=[first]+middle+[last]
        seq=sorted(times.get(trip,[]),key=lambda r:int(r['stop_sequence']))
        matches=[i for i in range(len(seq)-len(target)+1) if [r['stop_id'] for r in seq[i:i+len(target)]]==target]
        leg['v1_signals']=[]
        if not route or not leg.get('serviceDate') or len(matches)!=1:
            leg['v1_signal_status']='unavailable: trip or stop sequence ambiguous'; continue
        midnight=datetime.combine(date.fromisoformat(leg['serviceDate']),datetime.min.time(),tzinfo=timezone(timedelta(hours=5,minutes=30)))
        segment=seq[matches[0]:matches[0]+len(target)]
        boarding_h, boarding_m, boarding_s = map(int, segment[0]['departure_time'].split(':'))
        boarding = midnight + timedelta(hours=boarding_h, minutes=boarding_m, seconds=boarding_s)
        for current,nxt in zip(segment,segment[1:]):
            try:
                h,m,s=map(int,current['departure_time'].split(':'))
                if h < 0 or not 0 <= m < 60 or not 0 <= s < 60: raise ValueError('invalid time')
                crossing=midnight+timedelta(hours=h,minutes=m,seconds=s)
                lookup = boarding if timing_basis == 'boarding' else crossing
                key = (route, current['stop_id'], nxt['stop_id'], lookup.isoformat())
                if key not in signal_cache:
                    signal_cache[key] = query(database, *key)
                signal = signal_cache[key]
                leg['v1_signals'].append({'from_stop_id':current['stop_id'],'to_stop_id':nxt['stop_id'],'scheduled_time':crossing.isoformat(), 'model_lookup_time':lookup.isoformat(), 'model_timing_basis':timing_basis, 'status':signal['status'],'all_scheduled_days_proxy':signal.get('all_scheduled_days_proxy'), 'relative_crowding':signal.get('relative_crowding')})
            except (KeyError, ValueError):
                leg['v1_signals'].append({'from_stop_id':current['stop_id'],'to_stop_id':nxt['stop_id'],'status':'unavailable: invalid scheduled time'})
        leg['v1_signal_status']='attached; availability varies by segment'
    return itinerary
