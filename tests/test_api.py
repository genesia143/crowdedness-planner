import json
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from api import handler_for
from predict import create_database

class ApiTests(unittest.TestCase):
    def test_http_health_and_input_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p/'source.json').write_text(json.dumps({'training_start':'2026-10-01','training_end':'2026-10-21','definition':'sample','quality':{},'records':[]}))
            create_database(p/'source.json', p/'model.db')
            server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(p/'model.db'))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = 'http://127.0.0.1:' + str(server.server_port)
                with urlopen(base + '/health') as response:
                    self.assertEqual(json.load(response)['status'], 'ok')
                with self.assertRaises(HTTPError) as error:
                    urlopen(base + '/segments/signal')
                self.assertEqual(error.exception.code, 400)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

if __name__ == '__main__':
    unittest.main()
