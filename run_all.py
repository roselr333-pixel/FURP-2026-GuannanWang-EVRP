#!/usr/bin/env python3
"""
run_all.py — one-command reproduction of this project: every experiment script
(headline + week 1-5) and every figure in figures/ is a step below.

Usage:
    python run_all.py                         # uses the current interpreter (must have requirements installed)
    PYTHON=/path/to/venv/python run_all.py     # or force a specific interpreter

Each script writes its own CSV / log under src/results/ and figures under
figures/ (repo root). Scripts are ordered so that dependents are produced first:
the figure tools run last, after the experiments that write their input CSVs.
A full run takes roughly 1.5-2 hours on this machine; the self-written GA
baseline (70-90 min for its 5 seeds) is the slow one, the figures seconds each.
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
    ("OR-Tools vs BKS (56 Solomon)",        "benchmark_official_solomon.py",  "7.2-8.1% mean gap; time-budgeted GLS search"),
    ("PyVRP vs BKS (56 Solomon)",           "baseline_pyvrp_vrptw.py",        "-3.0% mean gap; deterministic"),
    ("Self-written GA vs BKS (56)",         "baseline_ga_vrptw.py",           "LONG ~70-90 min, 5 seeds"),
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
    ("V3 ablation (4 configs, EV+TW)",      "v3_ablation.py",                 "40 instances, same seeds as V3"),
    ("Std-instance ablation (W7 ext)",      "week07_ablation_std.py",         "48 standard instances, deterministic"),
    ("Drone energy/payload sweep",           "drone_energy_ablation.py",       "88 instances x BETA in {0, 0.02, 0.04}"),
    ("Exact optimality gap (CP-SAT)",       "week08_exact_gap.py",            "small n; exact optimum + heuristic gaps"),
    ("Paired significance tests",           "stat_tests.py",                  "Wilcoxon; reads W6/W7/W8 CSVs"),
    ("Capacity study (is CAP binding?)",    "week06_capacity_study.py",       "declared CAP=1000 and 600/400 vs total demand"),
    ("Standard-instance run (Schneider)",   "week06_standard_instances.py",   "real coordinates/TW/stations/battery, 6 families x 24 subsets"),
    # ---- week 1-5 experiments (small; included so one command covers them) ----
    ("Week 1 VRPTW smoke test",             "week01_baseline.py",             "5 customers; greedy + guided local search"),
    ("Week 3 fair comparison",              "week03_experiment.py",           "baseline vs 2-opt at n=10/20/40 + failure cases"),
    ("Week 3 baseline reproduction",        "week03_reproduce.py",            "Solomon-format instance"),
    ("Week 4 battery / charging study",     "week04_evrp_tw.py",              "battery x recharge trade-off"),
    ("Week 5 truck+drone (parallel)",       "week05_truck_drone.py",          "depot-only drone loop baseline"),
    ("Week 5 truck+drone (any node)",       "week05_truck_drone_v2.py",       "FSTSP-style launch/recover"),
    ("Week 6 ground-air EVRP-TW headline",  "week06_ground_air_evrp_tw.py",   "V0/V1/V2 + constraint failure cases"),
    ("EVRPTW benchmark (with stations)",    "benchmark_evrptw.py",            "Solomon customers + charging stations"),
    ("VRPTW size sweep",                    "benchmark_solomon_vrptw.py",     "generated instances, OR-Tools"),
    # ---- Schneider (2014) replication (its figures read the CSV below) ----
    ("Schneider E-VRPTW replication",       "schneider_evrptw.py",            "my EVRP-TW solver on the original 92 instances"),
    ("Schneider vs BKS comparison",         "schneider_bks_compare.py",       "reads the baseline CSV above"),
    # ---- figures (run last: they read the CSVs the experiments write) ----
    ("Figure: scale decay",                 "src/tools/gen_largen_figure.py",       "reads week06_largeN_summary.csv"),
    ("Figure: standard-instance ablation",  "src/tools/gen_ablation_std_figure.py", "reads week07_ablation_std_summary.csv"),
    ("Figure: V3 ablation",                 "src/tools/gen_v3_ablation_figure.py",  "reads v3_ablation_summary.csv"),
    ("Figure: drone energy",                "src/tools/gen_drone_energy_figure.py", "reads drone_energy_summary.csv"),
    ("Figure: LNS vs greedy",               "src/tools/plot_lns.py",                "reads week08_lns_summary.csv"),
    ("Figure: multi-drone",                 "src/tools/plot_multidrone.py",         "reads week08_multidrone_summary.csv"),
    ("Figure: multi-drone (standard)",      "src/tools/plot_multidrone_std.py",     "reads week08_multidrone_std_summary.csv"),
    ("Figure: exact optimality gap",        "src/tools/plot_exact_gap.py",          "reads week08_exact_gap_summary.csv"),
    ("Figure: capacity binding",            "src/tools/gen_capacity_figure.py",     "reads week06_capacity_summary.csv"),
    ("Figure: standard instances",          "src/tools/gen_std_instances_figure.py", "reads week06_std_evrp_summary.csv"),
    ("Figure: Schneider routes + vehicles", "src/tools/plot_schneider_routes.py",   "reads the Schneider comparison CSV"),
]


def main():
    print(f"Python : {PY}\nRepo   : {REPO}\n")
    results = []
    for label, script, note in STEPS:
        # entries like "src/tools/plot_lns.py" are repo-relative; the rest live
        # in src/experiments/
        path = (os.path.join(REPO, script) if script.startswith(("src/", "src" + os.sep))
                else os.path.join(EXP, script))
        if not os.path.exists(path):
            print(f"[SKIP] {label} — script not found: {path}")
            results.append((label, "MISSING", 0.0))
            continue
        t0 = time.time()
        print(f"[RUN ] {label}  ({note})")
        try:
            r = subprocess.run([PY, path], cwd=REPO,
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace",
                               env={**os.environ, "PYTHONIOENCODING": "utf-8"})
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
