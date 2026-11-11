"""Print the final results of the practice part in the terminal.

python show_results.py
"""
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(ROOT, "stand", "results")


def load(name):
    path = os.path.join(RES, f"metrics_{name}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def cell(m, key):
    if m is None:
        return "-"
    if key == "lat":
        return f"{m['p50_ms']:.0f} / {m['p95_ms']:.0f} / {m['p99_ms']:.0f}"
    if key == "rocof":
        return f"{m['rocof_per_h']:.1f} ({m['episodes']} ep.)"
    return f"{m[key]:.4f}"


def table(title, cols):
    given = {"pofod": "0.00020", "rocof": "0.0028", "avail": "0.98389", "lat": "-"}
    rows = [("POFOD", "pofod"), ("ROCOF, 1/h", "rocof"), ("AVAIL", "avail"), ("p50/p95/p99, ms", "lat")]
    head = ["Metric", "Given (720 h)"] + [c[0] for c in cols]
    data = [[lbl, given[k]] + [cell(m, k) for _, m in cols] for lbl, k in rows]
    widths = [max(len(str(r[i])) for r in [head] + data) + 2 for i in range(len(head))]
    sep = "+" + "+".join("-" * w for w in widths) + "+"
    print(f"\n{title}")
    print(sep)
    print("|" + "|".join(f" {h:<{w - 1}}" for h, w in zip(head, widths)) + "|")
    print(sep)
    for r in data:
        print("|" + "|".join(f" {str(v):<{w - 1}}" for v, w in zip(r, widths)) + "|")
    print(sep)


def main():
    print("=" * 72)
    print(" DariDrone (variant 5) - static stability: flight plan in memory")
    print(" Fault: dep-a (dispatcher) unavailable, HTTP 503, from 30 s to 60 s of 120 s")
    print("=" * 72)

    off, on = load("off"), load("on")
    table("LOCAL RUN (processes on this laptop)", [("PATTERN=off", off), ("PATTERN=on", on)])
    k_off, k_on = load("k8s_off"), load("k8s_on")
    if k_off or k_on:
        table("KUBERNETES RUN (kind cluster in Docker, core replicas R=3)",
              [("PATTERN=off", k_off), ("PATTERN=on", k_on)])

    print("\nHYPOTHESIS vs RESULT")
    checks = [
        ("off: POFOD ~ 0.25 (30 of 120 s broken)", off, lambda m: 0.2 <= m["pofod"] <= 0.3),
        ("off: AVAIL ~ 0.75", off, lambda m: 0.7 <= m["avail"] <= 0.8),
        ("on:  POFOD < 1 %", on, lambda m: m["pofod"] < 0.01),
        ("on:  AVAIL = 1.0", on, lambda m: m["avail"] == 1.0),
        ("on:  p95 < 50 ms", on, lambda m: m["p95_ms"] < 50),
    ]
    for text, m, ok in checks:
        res = "-" if m is None else ("CONFIRMED" if ok(m) else "NOT CONFIRMED")
        print(f"  {text:<44} {res}")

    print("\nCHANGE A PARAMETER AND PREDICT (pattern on)")
    scen = [
        ("on_maxage10", "PLAN_MAX_AGE_S=10", "POFOD ~ 0.167 (failsafe after 10 s)"),
        ("on_maxage120", "PLAN_MAX_AGE_S=120", "POFOD ~ 0 (limit never reached)"),
        ("on_delay2000", 'FAULT={"delay_ms": 2000}', "POFOD ~ 0, answers from memory"),
    ]
    for name, change, pred in scen:
        m = load(name)
        fact = "not run yet" if m is None else (
            f"POFOD={m['pofod']:.4f}  AVAIL={m['avail']:.4f}  p95={m['p95_ms']:.0f} ms")
        print(f"  {change:<26} predicted: {pred}")
        print(f"  {'':<26} actual:    {fact}")


if __name__ == "__main__":
    main()
