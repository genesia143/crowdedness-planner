"""Direct scheduled bus journeys. No transfers, walking or live positions."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from model import rows
from service import active_services
from predict import query, model_timing_basis

IST = timezone(timedelta(hours=5, minutes=30))


def gtfs_seconds(text):
    parts = text.split(':')
    if len(parts) != 3: raise ValueError('invalid GTFS time')
    h, m, s = map(int, parts)
    if not 0 <= h < 48 or not 0 <= m < 60 or not 0 <= s < 60: raise ValueError('unsupported GTFS time')
    return h * 3600 + m * 60 + s


class JourneyPlanner:
    def __init__(self, gtfs, database):
        self.gtfs, self.database = Path(gtfs), database
        if (self.gtfs/'frequencies.txt').exists(): raise ValueError('frequency-based service is not supported')
        stop_rows = list(rows(self.gtfs/'stops.txt'))
        self.stops = {r['stop_id']:r['stop_name'] for r in stop_rows}
        self.stop_coordinates = {}
        for r in stop_rows:
            try:
                self.stop_coordinates[r['stop_id']] = (float(r['stop_lat']), float(r['stop_lon']))
            except (KeyError, TypeError, ValueError):
                pass
        routes = {r['route_id']:r['route_short_name'] for r in rows(self.gtfs/'routes.txt')}
        self.trips = {r['trip_id']:(routes.get(r['route_id']),r['service_id']) for r in rows(self.gtfs/'trips.txt')}
        grouped = defaultdict(list)
        for r in rows(self.gtfs/'stop_times.txt'):
            if r['trip_id'] in self.trips:
                if not r.get('arrival_time') or not r.get('departure_time'):
                    raise ValueError('missing stop time; interpolation is not supported')
                grouped[r['trip_id']].append((int(r['stop_sequence']),r['stop_id'],gtfs_seconds(r['arrival_time']),gtfs_seconds(r['departure_time']),r.get('pickup_type',''),r.get('drop_off_type','')))
        self.by_stop = defaultdict(list)
        for trip, seq in grouped.items():
            seq.sort(); seq=tuple(seq)
            for i, stop in enumerate(seq[:-1]):
                if stop[4] in ('', '0'): self.by_stop[stop[1]].append((trip,seq,i))

    def search_stops(self, text, limit=20):
        if not text.strip(): raise ValueError('stop search query is required')
        if not 1 <= limit <= 50: raise ValueError('limit must be between 1 and 50')
        q=text.casefold().strip()
        return [{'stop_id':sid,'stop_name':name,'latitude':self.stop_coordinates.get(sid, (None,None))[0], 'longitude':self.stop_coordinates.get(sid, (None,None))[1]} for sid,name in sorted(self.stops.items(),key=lambda item:(item[1].casefold(),item[0])) if q in name.casefold()][:limit]

    def transfer_journeys(self, origin, destination, departure, limit=5):
        """One transfer at the exact same stop ID; no walking between stops."""
        if origin not in self.stops or destination not in self.stops: raise ValueError('unknown stop ID')
        if origin == destination: raise ValueError('origin and destination must be different')
        if not 1 <= limit <= 20: raise ValueError('limit must be between 1 and 20')
        from model import parse_timestamp
        requested=parse_timestamp(departure)
        if requested.utcoffset() is None: raise ValueError('departure must include a timezone offset')
        requested=requested.astimezone(IST)
        active=active_services(self.gtfs,requested.date()-timedelta(days=1),requested.date()+timedelta(days=1))
        def departures(stop, earliest, latest):
            for trip, seq, i in self.by_stop.get(stop, ()):
                route,service=self.trips[trip]
                if not route: continue
                for service_day, services in active.items():
                    if service not in services: continue
                    midnight=datetime.combine(service_day,datetime.min.time(),tzinfo=IST)
                    start=midnight+timedelta(seconds=seq[i][3])
                    if earliest <= start <= latest: yield trip,seq,i,route,midnight,start
        destinations={}
        for trip,seq,i,route,midnight,start in departures(origin,requested,requested+timedelta(hours=2)):
            for j in range(i+1,len(seq)):
                stop=seq[j]
                if stop[5] not in ('','0') or stop[1] in (origin,destination): continue
                arrival=midnight+timedelta(seconds=stop[2])
                if arrival < start or arrival > requested+timedelta(hours=4): continue
                destinations.setdefault(stop[1],[]).append((trip,route,start,arrival,seq,i,j,midnight))
        results=[]
        for stop,firsts in destinations.items():
            earliest=min(x[3] for x in firsts)+timedelta(minutes=5)
            latest=min(max(x[3] for x in firsts)+timedelta(minutes=60), requested+timedelta(hours=4))
            for second,seq,k,route,midnight,start in departures(stop,earliest,latest):
                for j in range(k+1,len(seq)):
                    if seq[j][1] != destination or seq[j][5] not in ('','0'): continue
                    arrival=midnight+timedelta(seconds=seq[j][2])
                    if arrival < start or arrival > requested+timedelta(hours=4): continue
                    for first,first_route,first_start,first_arrival,first_seq,first_i,first_j,first_midnight in firsts:
                        gap=(start-first_arrival).total_seconds()/60
                        if first==second or not 5 <= gap <= 60: continue
                        results.append((arrival,first_start,first_route,first,first_arrival,stop,second,route,start,gap))
        results.sort()
        output=[]
        for arrival,first_start,first_route,first,first_arrival,stop,second,route,start,gap in results[:limit]:
            output.append({'transfer_stop_id':stop,'transfer_stop_name':self.stops.get(stop,''),'transfer_wait_minutes':gap,'scheduled_arrival':arrival.isoformat(),'legs':[{'route':first_route,'trip_id':first,'from_stop_id':origin,'to_stop_id':stop,'scheduled_departure':first_start.isoformat(),'scheduled_arrival':first_arrival.isoformat()},{'route':route,'trip_id':second,'from_stop_id':stop,'to_stop_id':destination,'scheduled_departure':start.isoformat(),'scheduled_arrival':arrival.isoformat()}]})
        return {'journeys':output,'limitations':'One transfer at the same GTFS stop ID, with 5–60 minutes between buses; no transfer walking, no real-time predictions and no crowding signal on these legs yet.'}

    def journeys(self, origin, destination, departure, limit=5):
        if origin not in self.stops or destination not in self.stops: raise ValueError('unknown stop ID')
        if origin == destination: raise ValueError('origin and destination must be different')
        if not 1 <= limit <= 20: raise ValueError('limit must be between 1 and 20')
        from model import parse_timestamp
        dt=parse_timestamp(departure)
        if dt.utcoffset() is None: raise ValueError('departure must include a timezone offset')
        dt=dt.astimezone(IST)
        active=active_services(self.gtfs,dt.date()-timedelta(days=1),dt.date())
        choices=[]
        for trip, seq, i in self.by_stop.get(origin,()):
            route, service=self.trips[trip]
            if not route: continue
            for j in range(i+1,len(seq)):
                if seq[j][1] != destination or seq[j][5] not in ('', '0'): continue
                for service_day, services in active.items():
                    if service not in services: continue
                    midnight=datetime.combine(service_day,datetime.min.time(),tzinfo=IST)
                    depart=midnight+timedelta(seconds=seq[i][3]); arrive=midnight+timedelta(seconds=seq[j][2])
                    if not dt <= depart <= dt+timedelta(hours=2) or arrive < depart: continue
                    choices.append((arrive,depart,route,trip,seq,i,j,midnight))
        choices.sort(key=lambda v:(v[0],v[1],v[2],v[3]))
        result=[]
        timing_basis = model_timing_basis(self.database) if choices else None
        for arrive,depart,route,trip,seq,i,j,midnight in choices[:limit]:
            segments=[]
            for k in range(i,j):
                crossing=midnight+timedelta(seconds=seq[k][3])
                lookup = depart if timing_basis == 'boarding' else crossing
                signal=query(self.database,route,seq[k][1],seq[k+1][1],lookup.isoformat())
                segments.append({'from_stop_id':seq[k][1],'to_stop_id':seq[k+1][1], 'scheduled_time':crossing.isoformat(), 'model_lookup_time':lookup.isoformat(), 'model_timing_basis':timing_basis, 'signal':signal.get('scheduled_service_proxy'), 'all_scheduled_days_signal':signal.get('all_scheduled_days_proxy'), 'signal_status':signal['status'], 'relative_crowding':signal.get('relative_crowding')})
            result.append({'route':route,'trip_id':trip,'from_stop_id':origin,'to_stop_id':destination,'scheduled_departure':depart.isoformat(),'scheduled_arrival':arrive.isoformat(),'waiting_minutes':(depart-dt).total_seconds()/60,'ride_minutes':(arrive-depart).total_seconds()/60,'segments':segments})
        return {'origin':{'stop_id':origin,'name':self.stops[origin]},'destination':{'stop_id':destination,'name':self.stops[destination]},'requested_departure':dt.isoformat(),'journeys':result,'limitations':'Direct scheduled buses only, within two hours; no walking, transfers, live service or actual occupancy. Ticket creation time may differ from boarding time.'}
