"""Before / after the background-refresh fix (Kubernetes, core idle 75 s before the run).

python compare_fix.py
"""
import csv
import json
import os

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stand", "results")
RUNS = [("BEFORE fix", "k8s_before_fix", "BACKGROUND_REFRESH=off"),
        ("AFTER fix", "k8s_after_fix", "BACKGROUND_REFRESH=on")]


def load(name):
    with open(os.path.join(RES, f"metrics_{name}.json")) as f:
        m = json.load(f)
    with open(os.path.join(RES, f"{name}.csv")) as f:
        rows = [(float(r["t"]), int(r["status"])) for r in csv.DictReader(f)]
    m["fail_first_5s"] = sum(1 for t, s in rows if t < 5 and s != 200)
    m["fail_fault_window"] = sum(1 for t, s in rows if 30 <= t < 61 and s != 200)
    log = os.path.join(RES, f"{name}.log")
    m["failsafe_events"] = sum(1 for line in open(log) if "FAILSAFE" in line) if os.path.exists(log) else 0
    return m


def main():
    data = [(title, env, load(name)) for title, name, env in RUNS]
    rows = [
        ("core setting", lambda m, env: env),
        ("POFOD", lambda m, env: f"{m['pofod']:.4f}"),
        ("failed requests", lambda m, env: f"{m['failed']} of {m['total']}"),
        ("  in first 5 s (idle core)", lambda m, env: str(m["fail_first_5s"])),
        ("  in fault window 30-60 s", lambda m, env: str(m["fail_fault_window"])),
        ("failure episodes", lambda m, env: str(m["episodes"])),
        ("ROCOF, 1/h", lambda m, env: f"{m['rocof_per_h']:.1f}"),
        ("AVAIL", lambda m, env: f"{m['avail']:.4f}"),
        ("p50/p95/p99, ms", lambda m, env: f"{m['p50_ms']:.0f} / {m['p95_ms']:.0f} / {m['p99_ms']:.0f}"),
        ("FAILSAFE events in core logs", lambda m, env: str(m["failsafe_events"])),
    ]
    head = ["Metric"] + [t for t, _, _ in data]
    table = [[lbl] + [f(m, env) for _, env, m in data] for lbl, f in rows]
    w = [max(len(r[i]) for r in [head] + table) + 2 for i in range(len(head))]
    sep = "+" + "+".join("-" * x for x in w) + "+"
    line = lambda r: "|" + "|".join(f" {v:<{x - 1}}" for v, x in zip(r, w)) + "|"
    print("=" * len(sep))
    print(" BEFORE vs AFTER the fix: background refresh of the flight plan")
    print(" Kubernetes (kind in Docker), core R=3, PATTERN=on, core idle 75 s, then")
    print(" 120 s load, dep-a unavailable (503) from 30 s to 60 s")
    print("=" * len(sep))
    print(sep); print(line(head)); print(sep)
    for r in table:
        print(line(r))
    print(sep)
    b, a = data[0][2], data[1][2]
    print(f" Before: after idle the plan was older than 60 s -> first requests got FAILSAFE "
          f"({b['fail_first_5s']} failed).")
    print(f" After:  plan refreshed every 1 s in background -> {a['failed']} failed, POFOD={a['pofod']:.4f}, "
          f"AVAIL={a['avail']:.4f}.")


if __name__ == "__main__":
    main()
