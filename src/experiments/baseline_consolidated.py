"""
Consolidated baseline comparison for the ground-air EVRP-TW project.

Merges the three truck-only (no-drone) VRPTW baselines I have produced onto
the 56 Solomon instances, all referenced to BKS (best known solution):

  - OR-Tools   : commercial solver, primary truck baseline
  - GA         : my own metaheuristic (5-seed mean)
  - PyVRP      : community-standard open-source VRPTW solver (strongest)

Consolidating them states, on one
table, exactly where each baseline sits relative to BKS, and positions my
greedy truck-drone V2 correctly — V2 is a COLLABORATIVE heuristic that optimises
a makespan-driven objective, so its distance is not directly comparable to these
truck-only distance-minimising baselines. I report that difference.

Paths are resolved relative to this file, so the script runs from any CWD.

Outputs:
  src/results/baseline_consolidated.csv        (per-instance, 4 solvers + BKS)
  src/results/baseline_consolidated_summary.csv (per-family mean gap)
  figures/baseline_consolidated.png (grouped gap bars)
"""
import os
import csv
import statistics
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESULTS = os.path.join(REPO, "src", "results")
FIG_DIR = os.path.join(REPO, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

FAMILIES = ["C1", "C2", "R1", "R2", "RC1", "RC2"]


def family_of(name):
    for f in FAMILIES:
        if name.startswith(f):
            return f
    return "?"


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return {r["instance"]: r for r in csv.DictReader(fh)}


def main():
    comp = load_csv(os.path.join(RESULTS, "baseline_ga_vrptw_comparison.csv"))
    ga = load_csv(os.path.join(RESULTS, "baseline_ga_vrptw_results.csv"))
    pv = load_csv(os.path.join(RESULTS, "baseline_pyvrp_vrptw_results.csv"))

    instances = sorted(comp.keys())
    merged = {}
    for name in instances:
        c = comp[name]
        bks = float(c["bks_dist"])
        ort = float(c["ortools_dist"])
        ort_gap = float(c["ortools_gap"])
        g = ga[name]
        ga_mean = float(g["ga_dist_mean"])
        ga_gap = float(g["ga_gap_mean_pct"])
        ga_std = float(g["ga_gap_std_pct"])
        p = pv[name]
        pv_cost = float(p["pyvrp_cost"])
        pv_gap = float(p["pyvrp_gap_pct"])
        merged[name] = {
            "family": family_of(name),
            "bks": bks,
            "ortools": ort, "ortools_gap": ort_gap,
            "ga_mean": ga_mean, "ga_gap": ga_gap, "ga_std": ga_std,
            "pyvrp": pv_cost, "pyvrp_gap": pv_gap,
        }

    # ---- per-instance CSV ----
    out = os.path.join(RESULTS, "baseline_consolidated.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["instance", "family", "bks_dist",
                    "ortools_dist", "ortools_gap_pct",
                    "ga_dist_mean", "ga_gap_mean_pct", "ga_gap_std_pct",
                    "pyvrp_dist", "pyvrp_gap_pct"])
        for name in instances:
            m = merged[name]
            w.writerow([name, m["family"], round(m["bks"], 1),
                        round(m["ortools"], 1), round(m["ortools_gap"], 2),
                        round(m["ga_mean"], 1), round(m["ga_gap"], 2),
                        round(m["ga_std"], 2),
                        round(m["pyvrp"], 1), round(m["pyvrp_gap"], 2)])

    # ---- per-family summary ----
    fam = {f: {"ort": [], "ga": [], "pv": []} for f in FAMILIES}
    for name in instances:
        m = merged[name]
        f = m["family"]
        if f in fam:
            fam[f]["ort"].append(m["ortools_gap"])
            fam[f]["ga"].append(m["ga_gap"])
            fam[f]["pv"].append(m["pyvrp_gap"])

    summary = os.path.join(RESULTS, "baseline_consolidated_summary.csv")
    with open(summary, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["family", "n", "ortools_gap_mean", "ga_gap_mean",
                    "ga_gap_std", "pyvrp_gap_mean"])
        for f in FAMILIES:
            d = fam[f]
            n = len(d["ort"])
            row = [f, n,
                   round(statistics.mean(d["ort"]), 1),
                   round(statistics.mean(d["ga"]), 1),
                   round(statistics.pstdev(d["ga"]), 1),
                   round(statistics.mean(d["pv"]), 1)]
            w.writerow(row)

    overall = {
        "ort": [merged[n]["ortools_gap"] for n in instances],
        "ga": [merged[n]["ga_gap"] for n in instances],
        "pv": [merged[n]["pyvrp_gap"] for n in instances],
    }
    print("OVERALL mean gap vs BKS (n=%d):" % len(instances))
    print("  OR-Tools : %+.1f%%" % statistics.mean(overall["ort"]))
    print("  GA(5seed): %+.1f%%  (std %.1f)" % (
        statistics.mean(overall["ga"]), statistics.pstdev(overall["ga"])))
    print("  PyVRP    : %+.1f%%" % statistics.mean(overall["pv"]))

    # ---- figure: grouped bars per family ----
    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = np.arange(len(FAMILIES))
    wbar = 0.26
    ort_m = [statistics.mean(fam[f]["ort"]) for f in FAMILIES]
    ga_m = [statistics.mean(fam[f]["ga"]) for f in FAMILIES]
    pv_m = [statistics.mean(fam[f]["pv"]) for f in FAMILIES]
    ax.bar(x - wbar, ort_m, wbar, label="OR-Tools", color="#2c7fb8")
    ax.bar(x, ga_m, wbar, label="GA (5-seed)", color="#d95f02")
    ax.bar(x + wbar, pv_m, wbar, label="PyVRP", color="#31a354")
    ax.axhline(0, color="k", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(FAMILIES)
    ax.set_ylabel("mean gap to BKS (%)")
    ax.set_title("Truck-only VRPTW baselines vs BKS (56 Solomon instances)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fpath = os.path.join(FIG_DIR, "baseline_consolidated.png")
    fig.savefig(fpath, dpi=130)
    print("wrote", out)
    print("wrote", summary)
    print("wrote", fpath)


if __name__ == "__main__":
    main()
