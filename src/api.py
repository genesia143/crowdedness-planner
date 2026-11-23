"""Local, read-only demonstration API using Python's standard library."""
import argparse
import json
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from pathlib import Path
from predict import query


def mapped_journeys(params, database, planner, otp_endpoint, gtfs, recorded, fallback):
    """Plan with OTP or a recording; use the built-in planner when neither can answer."""
    fields = ['from_lat', 'from_lon', 'to_lat', 'to_lon', 'departure']
    if any(len(params.get(field, [])) != 1 for field in fields): raise ValueError('provide from_lat, from_lon, to_lat, to_lon and departure once each')
    if len(params.get('max_transfer_walk', [])) > 1: raise ValueError('provide max_transfer_walk at most once')
    values = [params[field][0] for field in fields] + [params.get('max_transfer_walk', ['1000'])[0]]
    for key in ('extra_minutes', 'latest_arrival'):
        if len(params.get(key, [])) > 1:
            raise ValueError('provide ' + key + ' at most once')
    from journey_choices import select_choices
    extra = params.get('extra_minutes', ['20'])[0]
    latest = params.get('latest_arrival', [None])[0]
    select_choices([], extra, latest)  # validate before calling routing services
    def with_choices(result):
        result['choices'] = select_choices(result['journeys'], extra, latest)
        return result
    def search_more(result, search):
        # A bounded set of later departure queries broadens the candidate set;
        # this is not an exhaustive search and must not be described as one.
        from otp_client import timing_breakdown
        requested = datetime.fromisoformat(values[4].replace('Z', '+00:00'))
        seen = set()
        def key(journey):
            return json.dumps([(leg.get('mode'), leg.get('start'), leg.get('end'), leg.get('route'),
                                leg.get('trip'), leg.get('from'), leg.get('to'), leg.get('intermediateStops'))
                               for leg in journey.get('legs', [])], sort_keys=True)
        for journey in result['journeys']:
            seen.add(key(journey))
        attempted, completed = [0], [0]
        for minutes in (10, 20):
            attempted.append(minutes)
            later_values = values[:]
            later_values[4] = (requested + timedelta(minutes=minutes)).isoformat()
            try:
                later = search(later_values)
            except (LookupError, OSError, RuntimeError):
                continue
            completed.append(minutes)
            for journey in later['journeys']:
                fingerprint = key(journey)
                if fingerprint not in seen:
                    seen.add(fingerprint)
                    # Wait includes time from the user's original requested departure.
                    timing_breakdown(journey, requested)
                    result['journeys'].append(journey)
        result['search_coverage'] = {'departure_offsets_minutes_attempted': attempted,
                                     'departure_offsets_minutes_completed': completed,
                                     'exhaustive': False,
                                     'note': 'Bounded later-departure searches; routing may omit alternatives.'}
        return with_choices(result)
    reason = 'mapped routing is not configured'
    if (otp_endpoint or recorded) and gtfs:
        from otp_client import fetch_otp, plan
        try:
            result = plan(otp_endpoint, gtfs, database, *values, fetch=recorded or fetch_otp,
                          stop_times=planner.trip_stop_times if planner is not None else None)
            result['routing_source'] = 'recorded OTP response' if recorded else 'OpenTripPlanner'
            return search_more(result, lambda vals: plan(otp_endpoint, gtfs, database, *vals,
                               fetch=recorded or fetch_otp,
                               stop_times=planner.trip_stop_times if planner is not None else None))
        except LookupError:
            reason = 'no recorded OTP response for this request'
        except OSError:
            # URLError and timeouts: OTP is configured but not reachable.
            reason = 'OpenTripPlanner is not reachable'
    if fallback is None: raise ValueError(reason)
    result = fallback.plan(*values)
    result['fallback_reason'] = reason
    return search_more(result, lambda vals: fallback.plan(*vals))


def handler_for(database, planner=None, otp_endpoint=None, gtfs=None, recorded=None):
    fallback = None
    if planner is not None:
        from fallback_planner import FallbackPlanner
        fallback = FallbackPlanner(planner)
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            try:
                if parsed.path == '/':
                    body = (Path(__file__).resolve().parent.parent / 'web' / 'index.html').read_bytes()
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if parsed.path == '/health':
                    result, status = {'status': 'ok'}, 200
                elif parsed.path == '/stops':
                    params = parse_qs(parsed.query)
                    if planner is None: raise ValueError('journey planner is not configured')
                    if len(params.get('q', [])) != 1: raise ValueError('provide q once')
                    result, status = {'stops': planner.search_stops(params['q'][0])}, 200
                elif parsed.path == '/journeys/mapped':
                    result = mapped_journeys(parse_qs(parsed.query), database, planner, otp_endpoint, gtfs, recorded, fallback)
                    status = 200
                elif parsed.path == '/journeys/transfers':
                    params = parse_qs(parsed.query)
                    if planner is None: raise ValueError('journey planner is not configured')
                    fields = ['from_stop_id','to_stop_id','departure']
                    if any(len(params.get(field, [])) != 1 for field in fields): raise ValueError('provide from_stop_id, to_stop_id, and departure once each')
                    result, status = planner.transfer_journeys(*(params[field][0] for field in fields)), 200
                elif parsed.path == '/journeys':
                    params = parse_qs(parsed.query)
                    if planner is None: raise ValueError('journey planner is not configured')
                    fields = ['from_stop_id','to_stop_id','departure']
                    if any(len(params.get(field, [])) != 1 for field in fields): raise ValueError('provide from_stop_id, to_stop_id, and departure once each')
                    result, status = planner.journeys(*(params[field][0] for field in fields)), 200
                elif parsed.path == '/segments/signal':
                    params = parse_qs(parsed.query)
                    fields = ['route', 'from_stop_id', 'to_stop_id', 'departure']
                    if any(len(params.get(field, [])) != 1 for field in fields):
                        raise ValueError('provide route, from_stop_id, to_stop_id, and departure once each')
                    result = query(database, *(params[field][0] for field in fields))
                    status = 200
                else:
                    result, status = {'error': 'not found'}, 404
            except ValueError as exc:
                result, status = {'error': str(exc)}, 400
            except Exception:
                # Do not expose local paths or database internals to clients.
                result, status = {'error': 'model unavailable'}, 503
            body = json.dumps(result).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
    return Handler

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', required=True)
    parser.add_argument('--gtfs', help='GTFS directory to enable stop search and journey planning')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--otp-endpoint', help='URL of a running OTP GraphQL endpoint')
    parser.add_argument('--otp-recordings', help='directory of recorded OTP responses (tests/fixtures/otp) to replay instead of a live OTP')
    args = parser.parse_args()
    from journeys import JourneyPlanner
    planner = JourneyPlanner(args.gtfs, args.database) if args.gtfs else None
    recorded = None
    if args.otp_recordings:
        from otp_client import RecordedOTP
        recorded = RecordedOTP(args.otp_recordings)
    ThreadingHTTPServer(('127.0.0.1', args.port), handler_for(args.database, planner, args.otp_endpoint, args.gtfs, recorded)).serve_forever()
