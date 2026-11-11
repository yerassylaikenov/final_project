"""loadgen: drones asking flight control for the next command.

20 requests/s for DURATION_S seconds, each waits at most 1.5 s.
CSV columns: t,status,latency_ms  (t = seconds from start, status 0 = client timeout)
OUT=<file> -> write CSV to the file and print progress; otherwise CSV goes to stdout.
"""
import os
import sys
import threading
import time
import urllib.error
import urllib.request

URL = os.environ.get("URL", "http://127.0.0.1:8080/")
RPS = int(os.environ.get("RPS", "20"))
DURATION_S = float(os.environ.get("DURATION_S", "120"))
CLIENT_TIMEOUT_S = float(os.environ.get("CLIENT_TIMEOUT_S", "1.5"))
OUT = os.environ.get("OUT")
START_AT = float(os.environ.get("START_AT", "0"))   # unix time to start (keeps experiment.sh in sync)

rows = []
rows_lock = threading.Lock()


def one_request(t0, t_start):
    start = time.monotonic()
    try:
        with urllib.request.urlopen(URL, timeout=CLIENT_TIMEOUT_S) as resp:
            resp.read()
            status = resp.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    except Exception:
        status = 0                                   # timeout / connection error
    latency = (time.monotonic() - start) * 1000
    with rows_lock:
        rows.append((t0 - t_start, status, latency))


def main():
    if START_AT > time.time():
        time.sleep(START_AT - time.time())
    t_start = time.monotonic()                      # monotonic: immune to wall-clock jumps
    threads = []
    n = int(DURATION_S * RPS)
    for i in range(n):
        t_plan = t_start + i / RPS
        delay = t_plan - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        th = threading.Thread(target=one_request, args=(time.monotonic(), t_start), daemon=True)
        th.start()
        threads.append(th)
        if OUT and i and i % (RPS * 10) == 0:
            with rows_lock:
                done = list(rows)
            ok = sum(1 for r in done if r[1] == 200)
            print(f"[loadgen] t={i // RPS:>3}s  sent={i:>4}  ok={ok}/{len(done)}", flush=True)
    for th in threads:
        th.join(CLIENT_TIMEOUT_S + 1)

    rows.sort()
    lines = ["t,status,latency_ms"] + [f"{t:.3f},{s},{lat:.1f}" for t, s, lat in rows]
    if OUT:
        with open(OUT, "w", newline="") as f:
            f.write("\n".join(lines) + "\n")
        print(f"[loadgen] done: {len(rows)} requests -> {OUT}", flush=True)
    else:
        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
