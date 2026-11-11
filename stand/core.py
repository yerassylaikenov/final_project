"""core: flight control service (key function of variant 5, RTO 1 min / RPO 0).

GET /        -> next waypoint / command for the drone (calls do_work)
GET /healthz -> readiness/liveness probe, never touches dep-a

Pattern (PATTERN=on): static stability - the flight plan is kept in memory.
The drone keeps flying on the last known plan when the dispatcher (dep-a) is lost.
"""
import json
import os
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", "8080"))
PATTERN = os.environ.get("PATTERN", "off") == "on"
DEP_URL = os.environ.get("DEP_URL", "http://127.0.0.1:8081/")
DEP_TIMEOUT_S = float(os.environ.get("DEP_TIMEOUT_S", "10"))          # off: wait long
DEP_TIMEOUT_ON_S = float(os.environ.get("DEP_TIMEOUT_ON_S", "0.3"))    # on: short refresh call
PLAN_REFRESH_S = float(os.environ.get("PLAN_REFRESH_S", "1"))          # refresh plan every 1 s
PLAN_MAX_AGE_S = float(os.environ.get("PLAN_MAX_AGE_S", "60"))         # = RTO of flight control

# Pre-flight plan: loaded before take-off, so a cold start does not need dep-a.
PREFLIGHT_PLAN = {
    "plan_version": 0,
    "waypoints": [
        {"id": "WP1", "lat": 51.1282, "lon": 71.4304, "alt_m": 120},
        {"id": "WP2", "lat": 51.1605, "lon": 71.4704, "alt_m": 120},
        {"id": "WP3", "lat": 51.1801, "lon": 71.5102, "alt_m": 90},
    ],
}


VERBOSE = True                                   # tests switch the event log off


def log(msg):
    if VERBOSE:
        print(msg, flush=True)


class Failsafe(Exception):
    """Plan is older than PLAN_MAX_AGE_S: flying on it is more dangerous than landing."""


def call_dep(timeout=None):
    with urllib.request.urlopen(DEP_URL, timeout=timeout or DEP_TIMEOUT_S) as resp:
        return json.loads(resp.read())


# ---- static stability: plan in memory ------------------------------------
_lock = threading.Lock()
_state = {}


def reset_state(plan=None, plan_time=None):
    """(Re)load the pre-flight plan. Used at start-up and by the tests."""
    _state.update(
        plan=dict(plan or PREFLIGHT_PLAN),
        plan_time=time.time() if plan_time is None else plan_time,
        fresh=False,          # True = last refresh from dep-a succeeded
        last_try=0.0,
        failsafe=False,
    )


reset_state()


def refresh_plan():
    """Try to get a newer plan. Only one thread at a time; errors never escape."""
    if not _lock.acquire(blocking=False):
        return                                   # someone is already refreshing
    try:
        _state["last_try"] = time.time()
        try:
            plan = call_dep(timeout=DEP_TIMEOUT_ON_S)
        except Exception as exc:                 # 503, timeout, connection refused...
            if _state["fresh"]:
                log(f"[core] dep-a lost ({exc.__class__.__name__}) -> "
                    f"flying on plan v{_state['plan']['plan_version']} from memory")
            _state["fresh"] = False
            return
        if not _state["fresh"]:
            log(f"[core] dep-a OK -> plan v{plan.get('plan_version')} loaded")
        _state.update(plan=plan, plan_time=time.time(), fresh=True)
    finally:
        _lock.release()


def do_work():
    if not PATTERN:
        return call_dep()                        # no pattern: every request needs dep-a

    if time.time() - _state["last_try"] >= PLAN_REFRESH_S:
        refresh_plan()                           # at most once per PLAN_REFRESH_S

    age = time.time() - _state["plan_time"]
    if age > PLAN_MAX_AGE_S:                     # safety limit of the pattern
        if not _state.get("failsafe"):
            _state["failsafe"] = True
            log(f"[core] plan too old ({age:.0f}s > {PLAN_MAX_AGE_S:.0f}s) -> "
                f"FAILSAFE: land_or_return_home")
        raise Failsafe(f"plan age {age:.1f}s > {PLAN_MAX_AGE_S}s")
    _state["failsafe"] = False

    plan = _state["plan"]
    return {
        "status": "ok" if _state["fresh"] else "static",
        "plan_version": plan.get("plan_version"),
        "plan_age_s": round(age, 2),
        "next_waypoint": plan["waypoints"][0],
    }


# ---- HTTP server -----------------------------------------------------------
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
        try:
            return self._send(200, do_work())
        except Failsafe as exc:
            return self._send(503, {"status": "failsafe", "action": "land_or_return_home",
                                    "reason": str(exc)})
        except Exception as exc:
            return self._send(500, {"error": f"{exc.__class__.__name__}: {exc}"})

    def log_message(self, *args):
        pass


def background_refresh():
    """Keep the plan fresh even when no requests come (idle drone on the pad)."""
    while True:
        refresh_plan()
        time.sleep(PLAN_REFRESH_S)


BACKGROUND_REFRESH = os.environ.get("BACKGROUND_REFRESH", "on") == "on"   # off = behaviour before the fix

if __name__ == "__main__":
    if PATTERN and BACKGROUND_REFRESH:
        threading.Thread(target=background_refresh, daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    server.daemon_threads = True
    print(f"[core] flight control on :{PORT}  PATTERN={'on' if PATTERN else 'off'}  "
          f"PLAN_MAX_AGE_S={PLAN_MAX_AGE_S}  BACKGROUND_REFRESH={'on' if BACKGROUND_REFRESH else 'off'}",
          flush=True)
    server.serve_forever()
