"""Local, read-only demonstration API using Python's standard library."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from predict import query


def handler_for(database, planner=None):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            try:
                if parsed.path == '/health':
                    result, status = {'status': 'ok'}, 200
                elif parsed.path == '/stops':
                    params = parse_qs(parsed.query)
                    if planner is None: raise ValueError('journey planner is not configured')
                    if len(params.get('q', [])) != 1: raise ValueError('provide q once')
                    result, status = {'stops': planner.search_stops(params['q'][0])}, 200
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
    args = parser.parse_args()
    from journeys import JourneyPlanner
    planner = JourneyPlanner(args.gtfs, args.database) if args.gtfs else None
    ThreadingHTTPServer(('127.0.0.1', args.port), handler_for(args.database, planner)).serve_forever()
