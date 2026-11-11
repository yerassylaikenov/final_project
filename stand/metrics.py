"""metrics.py: POFOD, failure episodes, ROCOF, AVAIL, p50/p95/p99 from a loadgen CSV.

Usage: python metrics.py results/off.csv [--json out.json]

Rules (see the exam slides):
  failure      = status != 200 (status 0 = client timeout)
  POFOD        = failed / total
  episode      = series of failures, gap between neighbours < 2 s
  ROCOF        = episodes / duration_h, duration = floor(t_max) - floor(t_min) + 1 seconds
  AVAIL        = share of seconds with at least one 200
  percentiles  = nearest rank: sorted latencies, element number ceil(p*n) (1-based)
"""
import csv
import json
import math
import sys

EPISODE_GAP_S = 2.0


def load(path):
    with open(path, newline="") as f:
        return [(float(r["t"]), int(r["status"]), float(r["latency_ms"])) for r in csv.DictReader(f)]


def percentile(sorted_values, p):
    k = max(1, math.ceil(p * len(sorted_values)))
    return sorted_values[k - 1]


def compute(rows):
    if not rows:
        raise ValueError("empty CSV")
    total = len(rows)
    fail_times = sorted(t for t, s, _ in rows if s != 200)

    episodes = 0
    prev = None
    for t in fail_times:
        if prev is None or t - prev >= EPISODE_GAP_S:
            episodes += 1
        prev = t

    first = math.floor(min(t for t, _, _ in rows))
    last = math.floor(max(t for t, _, _ in rows))
    seconds = last - first + 1
    ok_seconds = {math.floor(t) for t, s, _ in rows if s == 200}

    lat = sorted(l for _, _, l in rows)
    return {
        "total": total,
        "failed": len(fail_times),
        "pofod": len(fail_times) / total,
        "episodes": episodes,
        "duration_s": seconds,
        "rocof_per_h": episodes / (seconds / 3600),
        "avail": len(ok_seconds) / seconds,
        "p50_ms": percentile(lat, 0.50),
        "p95_ms": percentile(lat, 0.95),
        "p99_ms": percentile(lat, 0.99),
    }


def summary_line(m):
    return (f"POFOD={m['pofod']:.4f}  episodes={m['episodes']}  ROCOF={m['rocof_per_h']:.1f}/h  "
            f"AVAIL={m['avail']:.4f}  p50/p95/p99={m['p50_ms']:.0f}/{m['p95_ms']:.0f}/{m['p99_ms']:.0f} ms  "
            f"total={m['total']}")


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    m = compute(load(argv[0]))
    print(summary_line(m))
    if "--json" in argv:
        with open(argv[argv.index("--json") + 1], "w") as f:
            json.dump(m, f, indent=2)
    else:
        print(json.dumps(m))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
