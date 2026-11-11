"""dep-a: dispatcher service. Issues the current flight plan.

GET  /        -> {"plan_version": N, "waypoints": [...], "issued_at": ts}
GET  /healthz -> 200 ok
POST /fault   -> set a fault, e.g. {"unavailable": true}, {"delay_ms": 2000},
                 {"error_rate": 0.3}; POST {} repairs the service.
"""
import json
import os
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", "8081"))
PLAN_PERIOD_S = float(os.environ.get("PLAN_PERIOD_S", "10"))  # new plan version every 10 s
START = time.time()
FAULT = {}
LOCK = threading.Lock()

WAYPOINTS = [
    {"id": "WP1", "lat": 51.1282, "lon": 71.4304, "alt_m": 120},  # pharmacy hub
    {"id": "WP2", "lat": 51.1605, "lon": 71.4704, "alt_m": 120},
    {"id": "WP3", "lat": 51.1801, "lon": 71.5102, "alt_m": 90},   # rural clinic
]


def current_plan():
    version = int((time.time() - START) // PLAN_PERIOD_S) + 1
    return {"plan_version": version, "waypoints": WAYPOINTS, "issued_at": round(time.time(), 3)}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/healthz":
            return self._send(200, {"status": "ok"})
        with LOCK:
            fault = dict(FAULT)
        if fault.get("delay_ms"):
            time.sleep(fault["delay_ms"] / 1000)
        if fault.get("unavailable"):
            return self._send(503, {"error": "dispatcher unavailable"})
        if random.random() < float(fault.get("error_rate", 0)):
            return self._send(random.choice([500, 503]), {"error": "injected error"})
        return self._send(200, current_plan())

    def do_POST(self):
        if self.path != "/fault":
            return self._send(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        with LOCK:
            FAULT.clear()
            FAULT.update(body)
        print(f"[dep-a] fault set: {body or 'none (repaired)'}", flush=True)
        return self._send(200, {"fault": body})

    def log_message(self, *args):  # keep the console clean
        pass


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    server.daemon_threads = True
    print(f"[dep-a] dispatcher listening on :{PORT}", flush=True)
    server.serve_forever()
