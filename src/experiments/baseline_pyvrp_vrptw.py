"""
Baseline A — PyVRP as an additional, research-grade VRPTW solver.

Motivation (benchmarked against Frank/Ziqi, who both use PyVRP): OR-Tools is a
general CP-SAT solver; PyVRP is the dedicated VRP solver used throughout the
EVRP literature. Adding it as a third baseline (next to OR-Tools and my
self-written GA) directly strengthens the "baseline reproduction" part of the
project. The script solves the OFFICIAL SOLOMON VRPTW instances with PyVRP and compares
the total distance to the published BKS.

PyVRP reads VRPLIB Solomon files directly; no model construction needed.

Output:
  src/results/baseline_pyvrp_vrptw_results.csv   (per-instance)
  src/results/baseline_pyvrp_run.log             (console transcript of the run)
  figures/pyvrp_family_gap.png        (family mean gap bar)
"""
import os
import csv
import time

import pyvrp
from pyvrp.stop import MaxIterations

import baseline_ga_vrptw as bg

RESULTS_DIR = bg.RESULTS_DIR
INST_DIR = bg.INSTANCE_DIR
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV_PATH = os.path.join(RESULTS_DIR, "baseline_pyvrp_vrptw_results.csv")
RUN_LOG = os.path.join(RESULTS_DIR, "baseline_pyvrp_run.log")
FIG_PATH = os.path.join(REPO, "figures", "pyvrp_family_gap.png")
FAMILIES = bg.FAMILIES
ALL_INSTANCES = bg.ALL_INSTANCES
SEED = 42


def solve_one(name):
    path = os.path.join(INST_DIR, f"{name}.vrp")
    data = pyvrp.read(path)
    res = pyvrp.solve(data, stop=MaxIterations(3000), seed=SEED)
    cost = res.cost()
    feas = res.is_feasible()
    # PyVRP 0.14 exposes the route count on the best solution (res.summary is a
    # function, not an object, so res.summary.num_routes would always fail)
    n_routes = None
    try:
        n_routes = res.best.num_routes()
    except Exception:
        try:
            n_routes = len(res.best.routes())
        except Exception:
            pass
    return cost, feas, n_routes


def main():
    rows = []
    fam_gaps = {}
    log = []

    def emit(line=""):
        # everything the run prints is also kept, so the committed transcript
        # (baseline_pyvrp_run.log) is produced by this script itself
        print(line)
        log.append(line)

    emit(f"{'inst':<9}{'BKS':>9}{'PyVRP':>9}{'gap%':>9}{'veh':>5}{'feas':>6}")
    emit("-" * 48)
    for name in ALL_INSTANCES:
        bks = bg.load_instance(name)["bks_cost"]
        t0 = time.time()
        cost, feas, nr = solve_one(name)
        gap = (cost - bks) / bks * 100.0 if bks else 0.0
        fam = next(f for f, g in FAMILIES.items() if name in g)
        fam_gaps.setdefault(fam, []).append(gap)
        rows.append({"instance": name, "family": fam, "bks_cost": bks,
                     "pyvrp_cost": round(cost, 1),
                     "pyvrp_gap_pct": round(gap, 2),
                     "pyvrp_vehicles": nr,
                     "pyvrp_feasible": feas,
                     "runtime_s": round(time.time() - t0, 3)})
        emit(f"{name:<9}{bks:>9.1f}{cost:>9.1f}{gap:>9.1f}"
             f"{str(nr):>5}{str(feas):>6}")
    # family + overall mean gap
    fam_mean = {f: sum(v) / len(v) for f, v in fam_gaps.items()}
    all_gaps = [g for v in fam_gaps.values() for g in v]
    overall = sum(all_gaps) / len(all_gaps)
    emit("-" * 48)
    emit("FAMILY MEAN GAP (PyVRP vs BKS):")
    for f, gm in fam_mean.items():
        emit(f"  {f:<5} {gm:6.1f}%")
    emit(f"OVERALL mean gap = {overall:.1f}%  (n={len(all_gaps)})")

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["instance", "family", "bks_cost",
                                           "pyvrp_cost", "pyvrp_gap_pct",
                                           "pyvrp_vehicles", "pyvrp_feasible",
                                           "runtime_s"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
        w.writerow({"instance": "OVERALL", "family": "", "bks_cost": "",
                    "pyvrp_cost": "", "pyvrp_gap_pct": round(overall, 2),
                    "pyvrp_vehicles": "", "pyvrp_feasible": "",
                    "runtime_s": ""})
        for f, gm in fam_mean.items():
            w.writerow({"instance": f"FAM_{f}", "family": f, "bks_cost": "",
                        "pyvrp_cost": "", "pyvrp_gap_pct": round(gm, 2),
                        "pyvrp_vehicles": "", "pyvrp_feasible": "",
                        "runtime_s": ""})
    emit(f"wrote {CSV_PATH}")

    # bar chart of family mean gaps
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fams = list(fam_mean.keys())
        vals = [fam_mean[f] for f in fams]
        fig, ax = plt.subplots(figsize=(7, 4.5))
        bars = ax.bar(fams, vals, color="#756bb1")
        ax.axhline(overall, color="#d95f02", ls="--",
                   label=f"overall {overall:.1f}%")
        ax.axhline(7.2, color="#2c7fb8", ls=":", label="OR-Tools ~7.2% (prior)")
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.3, f"{v:.1f}",
                    ha="center", fontsize=9)
        ax.set_ylabel("mean gap to BKS (%)")
        ax.set_title("PyVRP baseline — Solomon VRPTW family mean gap")
        ax.legend()
        fig.tight_layout()
        os.makedirs(os.path.dirname(FIG_PATH), exist_ok=True)
        fig.savefig(FIG_PATH, dpi=130)
        emit(f"wrote {FIG_PATH}")
    except Exception as e:
        emit("figure skipped: " + str(e))

    with open(RUN_LOG, "w", encoding="utf-8") as fh:
        fh.write("\n".join(log) + "\n")
    print(f"wrote {RUN_LOG}")


if __name__ == "__main__":
    main()
