"""Rebuild everything: tests -> local runs -> calculations -> figures -> report PDF.

python build_all.py            # full (~12 min, five 2-minute runs)
python build_all.py --no-runs  # reuse CSV in stand/results (~1 min)
"""
import subprocess
import sys

PY = sys.executable
STEPS = [
    ("unit tests", [PY, "-m", "unittest", "-v"], "stand"),
    ("run off", [PY, "run_local.py", "off"], "stand"),
    ("run on", [PY, "run_local.py", "on"], "stand"),
    ("run on, PLAN_MAX_AGE_S=10", [PY, "run_local.py", "on", "--name", "on_maxage10", "--env", "PLAN_MAX_AGE_S=10"], "stand"),
    ("run on, PLAN_MAX_AGE_S=120", [PY, "run_local.py", "on", "--name", "on_maxage120", "--env", "PLAN_MAX_AGE_S=120"], "stand"),
    ("run on, delay 2000 ms", [PY, "run_local.py", "on", "--name", "on_delay2000", "--fault", '{"delay_ms": 2000}'], "stand"),
    ("calculations", [PY, "analysis/calc.py"], "."),
    ("figures", [PY, "analysis/figures.py"], "."),
    ("report", [PY, "report/build_report.py"], "."),
    ("summary", [PY, "show_results.py"], "."),
]

for name, cmd, cwd in STEPS:
    if "--no-runs" in sys.argv and name.startswith("run "):
        continue
    print(f"\n===== {name} =====", flush=True)
    if subprocess.run(cmd, cwd=cwd).returncode != 0:
        sys.exit(f"step failed: {name}")
print("\nALL STEPS OK")
