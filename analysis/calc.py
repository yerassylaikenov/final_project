"""All calculations of variant 5 (tasks 3, 4, 5, 6) + stand comparison.

python analysis/calc.py   -> prints the results and writes analysis/results.json
"""
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "stand", "results")

# ---- given data, variant 5 --------------------------------------------------
GIVEN = {
    "A": {"name": "Flight Control API (dispatcher server)", "mtbf_h": 1680, "mttr_h": 3},
    "B": {"name": "Flight plan & telemetry DB", "mtbf_h": 1600, "mttr_h": 6},
    "C": {"name": "LTE link of mobile operator (external)", "sla": 0.993},
    "trial": {"hours": 720, "requests": 54000, "failed_requests": 11,
              "service_failures": 2, "downtime_h": 11.6},
    "lef": (3, 4, 11),            # events / year
    "lm": (10, 26, 66),           # mln KZT
    "lm_after": (1.1, 2.9, 7.3),  # mln KZT
    "control_cost": 86,           # mln KZT / year
}
HOURS_PER_YEAR = 8760

# Task 3: risk register (probability, impact on 1..5)
RISKS = [
    ("R1", "Loss of link with dispatcher (LTE)", 4, 5, "Address"),
    ("R2", "Dispatcher server failure (A)", 3, 5, "Address"),
    ("R3", "Flight plan DB failure (B)", 2, 4, "Address"),
    ("R4", "GPS spoofing / jamming", 2, 5, "Address + Transfer"),
    ("R5", "Wrong flight plan (over people / no-fly zone)", 2, 5, "Address"),
    ("R6", "Command link compromise (spoofed commands)", 2, 5, "Address"),
    ("R7", "Dangerous weather (wind, icing)", 3, 3, "Avoid"),
    ("R8", "External weather service outage", 2, 2, "Accept"),
]


def pert(t):
    lo, ml, hi = t
    return (lo + 4 * ml + hi) / 6


def availability(mtbf, mttr):
    return mtbf / (mtbf + mttr)


def parallel(a, n=2):
    return 1 - (1 - a) ** n


def zone(score):
    return "critical" if score >= 15 else ("high/medium" if score >= 8 else "low")


def stand_metrics():
    out = {}
    for path in sorted(glob.glob(os.path.join(RESULTS_DIR, "metrics_*.json"))):
        name = os.path.basename(path)[len("metrics_"):-len(".json")]
        with open(path) as f:
            out[name] = json.load(f)
    return out


def compute():
    a_a = availability(GIVEN["A"]["mtbf_h"], GIVEN["A"]["mttr_h"])
    a_b = availability(GIVEN["B"]["mtbf_h"], GIVEN["B"]["mttr_h"])
    a_c = GIVEN["C"]["sla"]
    serial = a_a * a_b * a_c
    dup = parallel(a_a) * parallel(a_b) * a_c

    lef, lm, lm_after = pert(GIVEN["lef"]), pert(GIVEN["lm"]), pert(GIVEN["lm_after"])
    ale, ale_after = lef * lm, lef * lm_after
    cost = GIVEN["control_cost"]
    rosi = (ale - ale_after - cost) / cost

    tr = GIVEN["trial"]
    return {
        "task4": {
            "A_A": a_a, "A_B": a_b, "A_C": a_c,
            "downtime_A_h": (1 - a_a) * HOURS_PER_YEAR,
            "downtime_B_h": (1 - a_b) * HOURS_PER_YEAR,
            "downtime_C_h": (1 - a_c) * HOURS_PER_YEAR,
            "A_A_dup": parallel(a_a), "A_B_dup": parallel(a_b),
            "system_serial": serial, "downtime_serial_h": (1 - serial) * HOURS_PER_YEAR,
            "system_dup": dup, "downtime_dup_h": (1 - dup) * HOURS_PER_YEAR,
        },
        "task5": {
            "lef": lef, "lm": lm, "lm_after": lm_after,
            "ale_before": ale, "ale_after": ale_after, "cost": cost, "rosi": rosi,
            # ROSI < 0 when LEF * (LM - LM_after) < cost
            "lef_break_even": cost / (lm - lm_after),
        },
        "task6": {
            "pofod": tr["failed_requests"] / tr["requests"],
            "rocof_per_h": tr["service_failures"] / tr["hours"],
            "mean_days_between_failures": tr["hours"] / tr["service_failures"] / 24,
            "avail": (tr["hours"] - tr["downtime_h"]) / tr["hours"],
        },
        "risks": [
            {"id": i, "name": n, "p": p, "i": im, "score": p * im, "zone": zone(p * im), "strategy": s}
            for i, n, p, im, s in RISKS
        ],
        "stand": stand_metrics(),
        "given": GIVEN,
    }


def fmt_pp(v):
    return f"{v:.4f}"


def main():
    r = compute()
    t4, t5, t6 = r["task4"], r["task5"], r["task6"]
    line = "-" * 66
    print(line)
    print("VARIANT 5 - Drone delivery of medicines (DariDrone)")
    print(line)
    print("TASK 4. Availability  A = MTBF / (MTBF + MTTR)")
    print(f"  A  Flight Control API   1680/(1680+3)   = {t4['A_A']:.5f}   downtime {t4['downtime_A_h']:.1f} h/yr")
    print(f"  B  Flight plan DB       1600/(1600+6)   = {t4['A_B']:.5f}   downtime {t4['downtime_B_h']:.1f} h/yr")
    print(f"  C  LTE operator (SLA)                   = {t4['A_C']:.5f}   downtime {t4['downtime_C_h']:.1f} h/yr")
    print(f"  System A*B*C (serial)                   = {t4['system_serial']:.5f}   downtime {t4['downtime_serial_h']:.1f} h/yr")
    print(f"  After duplicating A and B               = {t4['system_dup']:.5f}   downtime {t4['downtime_dup_h']:.1f} h/yr")
    print("  -> after duplication the system is limited by the SLA of C (0.993)")
    print(line)
    print("TASK 5. FAIR  PERT = (min + 4*ML + max) / 6")
    print(f"  LEF          (3 + 4*4 + 11)/6        = {t5['lef']:.2f} events/yr")
    print(f"  LM           (10 + 4*26 + 66)/6      = {t5['lm']:.2f} mln KZT")
    print(f"  LM after     (1.1 + 4*2.9 + 7.3)/6   = {t5['lm_after']:.2f} mln KZT")
    print(f"  ALE before   LEF * LM                = {t5['ale_before']:.1f} mln KZT/yr")
    print(f"  ALE after    LEF * LM_after          = {t5['ale_after']:.1f} mln KZT/yr")
    print(f"  ROSI         (ALE - ALE_after - 86)/86 = {t5['rosi']:.2f}  (positive -> control pays off)")
    print(f"  ROSI turns negative if LEF < {t5['lef_break_even']:.2f} events/yr")
    print(line)
    print("TASK 6. Given 720 h trial")
    print(f"  POFOD  11 / 54000          = {t6['pofod']:.5f}")
    print(f"  ROCOF  2 / 720 h           = {t6['rocof_per_h']:.4f} 1/h  (~1 per {t6['mean_days_between_failures']:.0f} days)")
    print(f"  AVAIL  (720 - 11.6) / 720  = {t6['avail']:.5f}")
    print(line)
    print("TASK 3. Risk register (score = P x I)")
    for k in r["risks"]:
        print(f"  {k['id']}  {k['name']:<46} {k['p']}x{k['i']} = {k['score']:>2}  {k['zone']:<11} {k['strategy']}")
    print(line)
    if r["stand"]:
        print("STAND (measured): " + ", ".join(r["stand"]))
    out = os.path.join(ROOT, "analysis", "results.json")
    with open(out, "w") as f:
        json.dump(r, f, indent=2, ensure_ascii=False)
    print(f"saved {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    main()
