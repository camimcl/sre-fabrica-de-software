"""Controlled local target: no proxying or access to external services."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import time


class Target(BaseHTTPRequestHandler):
    def do_GET(self):
        time.sleep(0.4 if self.path == '/slow' else 0.03)
        self.send_response(503 if self.path == '/error' else 200)
        self.end_headers()
        self.wfile.write(b'LoadForge isolated QA target')

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', 8080), Target).serve_forever()
