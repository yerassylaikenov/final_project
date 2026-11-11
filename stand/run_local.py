"""Run the experiment on 127.0.0.1 (no cluster): dep-a + core + loadgen as processes.

Timeline (same as experiment.sh): 0 s start load, 30 s break dep-a, 60 s repair, 120 s end.

  python run_local.py off
  python run_local.py on
  python run_local.py on --name on_maxage10 --env PLAN_MAX_AGE_S=10
  python run_local.py on --name on_delay2000 --fault "{\"delay_ms\": 2000}"
  python run_local.py on --quick          # 30 s run: fault 10-20 s (for a live demo)
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request

import metrics

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
DEP_PORT, CORE_PORT = 18081, 18080
DEFAULT_FAULT = '{"unavailable": true}'          # variant 5: dep-a unavailable (503)


def post_fault(body):
    req = urllib.request.Request(f"http://127.0.0.1:{DEP_PORT}/fault", data=body.encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    urllib.request.urlopen(req, timeout=2).read()


def wait_ready(port):
    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=0.5).read()
            return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError(f"service on :{port} did not start")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["off", "on"])
    ap.add_argument("--name", help="result name (default: mode)")
    ap.add_argument("--fault", default=os.environ.get("FAULT", DEFAULT_FAULT))
    ap.add_argument("--env", action="append", default=[], help="extra env for core, KEY=VALUE")
    ap.add_argument("--quick", action="store_true", help="30 s run, fault 10-20 s")
    a = ap.parse_args()

    duration, f_start, f_end = (30, 10, 20) if a.quick else (120, 30, 60)
    name = a.name or a.mode + ("_quick" if a.quick else "")
    os.makedirs(RESULTS, exist_ok=True)
    csv_path = os.path.join(RESULTS, f"{name}.csv")
    log_path = os.path.join(RESULTS, f"{name}.log")

    env = dict(os.environ, PYTHONUNBUFFERED="1")
    core_env = dict(env, PORT=str(CORE_PORT), PATTERN=a.mode,
                    DEP_URL=f"http://127.0.0.1:{DEP_PORT}/")
    for kv in a.env:
        k, v = kv.split("=", 1)
        core_env[k] = v

    log = open(log_path, "w")

    def say(msg):
        line = f"[run {time.strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        log.write(line + "\n")
        log.flush()

    say(f"experiment '{name}': PATTERN={a.mode} FAULT={a.fault} "
        f"timeline 0/{f_start}/{f_end}/{duration} s {' '.join(a.env)}")
    procs = [
        subprocess.Popen([sys.executable, "dep.py"], cwd=HERE, stdout=log, stderr=log,
                         env=dict(env, PORT=str(DEP_PORT))),
        subprocess.Popen([sys.executable, "core.py"], cwd=HERE, stdout=log, stderr=log, env=core_env),
    ]
    try:
        wait_ready(DEP_PORT)
        wait_ready(CORE_PORT)
        say("dep-a and core are up, starting loadgen (20 rps, client timeout 1.5 s)")
        load = subprocess.Popen([sys.executable, "loadgen.py"], cwd=HERE, env=dict(
            env, URL=f"http://127.0.0.1:{CORE_PORT}/", DURATION_S=str(duration), OUT=csv_path))
        t0 = time.time()
        time.sleep(max(0, f_start - (time.time() - t0)))
        post_fault(a.fault)
        say(f"t={f_start}s  dep-a BROKEN: {a.fault}")
        time.sleep(max(0, f_end - (time.time() - t0)))
        post_fault("{}")
        say(f"t={f_end}s  dep-a REPAIRED")
        load.wait()
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            p.wait()

    m = metrics.compute(metrics.load(csv_path))
    m.update(name=name, mode=a.mode, fault=a.fault, env=a.env, source="local run")
    with open(os.path.join(RESULTS, f"metrics_{name}.json"), "w") as f:
        json.dump(m, f, indent=2)
    say("RESULT " + metrics.summary_line(m))
    say(f"saved: results/{name}.csv, results/{name}.log, results/metrics_{name}.json")
    log.close()


if __name__ == "__main__":
    main()
