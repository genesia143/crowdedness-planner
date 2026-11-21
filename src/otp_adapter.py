"""Helpers for the local OpenTripPlanner trial, not a production router."""
from datetime import date, datetime, timedelta, timezone
from model import rows
from predict import query


def transfer_walks_within_limit(legs, maximum_metres=1000):
    """Check contiguous walking legs between bus legs; reject unknown distances."""
    if maximum_metres < 0: raise ValueError('maximum distance must not be negative')
    transit=[i for i,leg in enumerate(legs) if leg.get('mode') == 'BUS']
    for first, second in zip(transit,transit[1:]):
        between=legs[first+1:second]
        if any(leg.get('mode') != 'WALK' or leg.get('distance') is None or leg['distance'] < 0 for leg in between):
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
        for current,nxt in zip(segment,segment[1:]):
            try:
                h,m,s=map(int,current['departure_time'].split(':'))
                if h < 0 or not 0 <= m < 60 or not 0 <= s < 60: raise ValueError('invalid time')
                crossing=midnight+timedelta(hours=h,minutes=m,seconds=s)
                signal=query(database,route,current['stop_id'],nxt['stop_id'],crossing.isoformat())
                leg['v1_signals'].append({'from_stop_id':current['stop_id'],'to_stop_id':nxt['stop_id'],'scheduled_time':crossing.isoformat(),'status':signal['status'],'all_scheduled_days_proxy':signal.get('all_scheduled_days_proxy')})
            except (KeyError, ValueError):
                leg['v1_signals'].append({'from_stop_id':current['stop_id'],'to_stop_id':nxt['stop_id'],'status':'unavailable: invalid scheduled time'})
        leg['v1_signal_status']='attached; availability varies by segment'
    return itinerary
