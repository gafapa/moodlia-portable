from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import sys
import threading
import unittest
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from local_proxy import create_proxy
from portable import free_port


class ProxyTests(unittest.TestCase):
    def test_mcp_can_call_rest_without_reentering_its_php_worker(self):
        proxy_port = free_port()
        workers = []

        class Worker(BaseHTTPRequestHandler):
            def log_message(self, *arguments):
                pass

            def do_GET(self):
                body = b'core-response'
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                self.rfile.read(int(self.headers.get('Content-Length', '0')))
                with urllib.request.urlopen(f'http://127.0.0.1:{proxy_port}/webservice/rest/server.php', timeout=3) as response:
                    body = response.read()
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        for index in range(3):
            server = HTTPServer(('127.0.0.1', 0), Worker)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            workers.append(server)
        proxy = create_proxy(proxy_port, [worker.server_address[1] for worker in workers])
        try:
            request = urllib.request.Request(f'http://127.0.0.1:{proxy_port}/local/moodlia/mcp.php', data=b'{}')
            with urllib.request.urlopen(request, timeout=5) as response:
                self.assertEqual(response.read(), b'core-response')
            request = urllib.request.Request(f'http://127.0.0.1:{proxy_port}/', headers={'Host': 'attacker.invalid'})
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(request, timeout=3)
            self.assertEqual(error.exception.code, 400)
        finally:
            proxy.shutdown()
            proxy.server_close()
            for worker in workers:
                worker.shutdown()
                worker.server_close()
