"""Receptor HTTP de demonstração, restrito ao loopback."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class AntifraudHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/antifraud":
            self.send_error(404)
            return
        event = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        print(json.dumps(event), flush=True)
        self.send_response(204)
        self.end_headers()


if __name__ == "__main__":
    print("Webhook em http://127.0.0.1:9001/antifraud", flush=True)
    with HTTPServer(("127.0.0.1", 9001), AntifraudHandler) as server:
        server.serve_forever()
