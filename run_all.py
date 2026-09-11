#!/usr/bin/env python3
"""
run_all.py — one-command reproduction of every headline experiment in this project.

Usage:
    python run_all.py                         # uses the current interpreter (must have requirements installed)
    PYTHON=/path/to/venv/python run_all.py     # or force a specific interpreter

Each script writes its own CSV / log under src/results/ and figures under
figures/ (repo root). Scripts are ordered so that dependents (e.g.
baseline_consolidated.py reads the three baseline CSVs) are produced first.
A full run takes roughly 40-60 minutes; the self-written GA baseline is the slow one.
"""
import subprocess
import sys
import os
import time

REPO = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.join(REPO, "src", "experiments")
PY = os.environ.get("PYTHON", sys.executable)

# (label, script filename, note)
STEPS = [
    ("OR-Tools vs BKS (56 Solomon)",        "benchmark_official_solomon.py",  "7.2% mean gap; deterministic"),
    ("PyVRP vs BKS (56 Solomon)",           "baseline_pyvrp_vrptw.py",        "-3.0% mean gap; deterministic"),
    ("Self-written GA vs BKS (56)",         "baseline_ga_vrptw.py",           "LONG ~35 min, 5 seeds"),
    ("3-baseline consolidation",            "baseline_consolidated.py",       "reads the 3 CSVs above"),
    ("Parameter sensitivity",               "week06_sensitivity.py",          "5 seeds x 4 params (R fixed 09-10)"),
    ("Multi-objective tradeoff",            "week06_multi_objective.py",      "weighted-sum, 5 weights x 5 seeds"),
    ("Controlled ablation (5 configs)",     "week07_improvement_ablation.py", "40 instances, sanity check"),
    ("FSTSP repro vs M&C (2015)",           "week07_fstsp_repro.py",          "40 instances"),
    ("Scaling decay (N=30/50/100)",         "week06_largeN.py",               "5 seeds"),
    ("LNS improvement (W8)",                "week08_lns.py",                  "60 instances, deterministic"),
    ("Multi-drone K=1/2/3 (W8 ext)",        "week08_multidrone.py",           "K-drone greedy + LNS, deterministic"),
    ("Std instances + K=1/2/3/5 + sched",   "week08_multidrone_std.py",       "Solomon-derived, optimal drone schedule + LB certificate"),
    ("M&C 2015 original FSTSP benchmark",   "week08_mc_benchmark.py",         "36 original instances, deterministic"),
    ("V3 EV+TW+drone collaboration",        "v3_ev_collab.py",                "4 sizes x 10 seeds, deterministic"),
    ("Paired significance tests",           "stat_tests.py",                  "Wilcoxon; reads W6/W7/W8 CSVs"),
]


def main():
    print(f"Python : {PY}\nRepo   : {REPO}\n")
    results = []
    for label, script, note in STEPS:
        path = os.path.join(EXP, script)
        if not os.path.exists(path):
            print(f"[SKIP] {label} — script not found: {path}")
            results.append((label, "MISSING", 0.0))
            continue
        t0 = time.time()
        print(f"[RUN ] {label}  ({note})")
        try:
            r = subprocess.run([PY, path], cwd=REPO,
                               capture_output=True, text=True)
            dt = time.time() - t0
            if r.returncode == 0:
                print(f"  OK   ({dt:.1f}s)")
                results.append((label, "OK", dt))
            else:
                tail = r.stderr.strip().splitlines()[-12:]
                print(f"  FAIL ({dt:.1f}s)\n" + "\n".join("    " + l for l in tail))
                results.append((label, "FAIL", dt))
        except Exception as e:  # pragma: no cover
            print(f"  ERROR {e}")
            results.append((label, "ERROR", 0.0))

    print("\n=== Summary ===")
    for label, status, dt in results:
        print(f"  {status:6}  {dt:6.1f}s  {label}")
    fails = [l for l, s, _ in results if s not in ("OK",)]
    if fails:
        print(f"\n{len(fails)} step(s) not OK; see stderr above.")
        print("CSVs are git-ignored by design — re-run to regenerate them locally.")


if __name__ == "__main__":
    main()
