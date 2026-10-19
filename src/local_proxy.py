"""Loopback proxy with a dedicated PHP worker for MCP's nested REST calls."""
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import urllib.parse

HOP_HEADERS = {'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
               'te', 'trailer', 'transfer-encoding', 'upgrade'}


def create_proxy(port, worker_ports):
    counter = 0
    mutex = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, *arguments):
            pass

        def forward(self):
            nonlocal counter
            self.close_connection = True
            parsed = urllib.parse.urlsplit(self.path)
            if parsed.scheme or parsed.netloc or self.headers.get('Host') != f'127.0.0.1:{port}':
                self.send_error(400, 'Invalid local request')
                return
            if self.headers.get('Transfer-Encoding'):
                self.send_error(400, 'A Content-Length request is required')
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if length < 0 or length > 256 * 1024 * 1024:
                    self.send_error(413)
                    return
            except ValueError:
                self.send_error(400)
                return
            if urllib.parse.unquote(parsed.path) == '/local/moodlia/mcp.php':
                upstream_port = worker_ports[0]
            else:
                with mutex:
                    upstream_port = worker_ports[1 + counter % (len(worker_ports) - 1)]
                    counter += 1
            connection = http.client.HTTPConnection('127.0.0.1', upstream_port, timeout=300)
            headers_sent = False
            try:
                connection.putrequest(self.command, self.path, skip_host=True, skip_accept_encoding=True)
                for name, value in self.headers.items():
                    if name.lower() not in HOP_HEADERS:
                        connection.putheader(name, value)
                connection.putheader('Connection', 'close')
                connection.endheaders()
                remaining = length
                while remaining:
                    chunk = self.rfile.read(min(remaining, 65536))
                    if not chunk:
                        raise ConnectionError('Incomplete request')
                    connection.send(chunk)
                    remaining -= len(chunk)
                response = connection.getresponse()
                self.send_response(response.status, response.reason)
                for name, value in response.getheaders():
                    if name.lower() not in HOP_HEADERS and name.lower() not in ('server', 'date'):
                        self.send_header(name, value)
                self.send_header('Connection', 'close')
                self.end_headers()
                headers_sent = True
                if self.command != 'HEAD':
                    while chunk := response.read(65536):
                        self.wfile.write(chunk)
            except (OSError, http.client.HTTPException):
                if not headers_sent:
                    self.send_error(502, 'Local Moodle is starting or unavailable')
            finally:
                connection.close()

        do_GET = forward
        do_POST = forward
        do_HEAD = forward
        do_OPTIONS = forward
        do_DELETE = forward
        do_PUT = forward

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
