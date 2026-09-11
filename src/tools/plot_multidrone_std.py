"""
Plot figures/multidrone_std.png from the standard-instance experiment.

Panel A: LNS benefit vs truck-only by size, for K = 1 / 2 / 3 / 5 drones.
Panel B: scheduling -- mean makespan under greedy vs local-search assignment
         (and the exact optimum where available).

Reads src/results/week08_multidrone_std_summary.csv and week08_scheduling.csv
(git-ignored; regenerate with week08_multidrone_std.py).

Run:
  python src/tools/plot_multidrone_std.py
"""

import os
import csv

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    here = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    res = os.path.join(here, "src", "results")
    figdir = os.path.join(here, "figures")
    os.makedirs(figdir, exist_ok=True)

    with open(os.path.join(res, "week08_multidrone_std_summary.csv"),
              newline="") as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: int(r["size"]))
    with open(os.path.join(res, "week08_scheduling.csv"), newline="") as f:
        sched = list(csv.DictReader(f))

    sizes = [r["size"] for r in rows]
    x = list(range(len(sizes)))
    Ks = [1, 2, 3, 5]
    colors = {1: "#f0a24b", 2: "#2e7d5b", 3: "#534ab7", 5: "#993c1d"}
    g = lambda r, k: float(r[k])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.6))
    for K in Ks:
        vals = [g(r, f"K{K}_lns_imp_vs_truck_pct") for r in rows]
        ax1.plot(x, vals, "-o", color=colors[K], label=f"K={K} drones")
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"N={s}" for s in sizes])
    ax1.set_ylabel("LNS benefit vs truck-only (%)")
    ax1.set_title("A. Standard Solomon instances: benefit vs drone count")
    ax1.legend(fontsize=8, frameon=False)
    ax1.grid(alpha=0.25)

    # panel B: how far the naive earliest-available rule is from the exact
    # optimum / from a local-search assignment
    import statistics
    ks = sorted({int(r["K"]) for r in sched})
    xs = list(range(len(ks)))
    loc_gap = [statistics.mean([float(r["local_gain_pct"]) for r in sched
                                if int(r["K"]) == k]) for k in ks]
    opt_gap = [statistics.mean([float(r["greedy_gap_to_opt_pct"]) for r in sched
                                if int(r["K"]) == k
                                and r["sched_optimal_mk"] != ""])
               for k in ks]
    w = 0.36
    ax2.bar([i - w / 2 for i in xs], loc_gap, w,
            label="local-search gain over naive rule", color="#2e7d5b")
    ax2.bar([i + w / 2 for i in xs], opt_gap, w,
            label="naive rule's gap to the exact optimum", color="#534ab7")
    for i, v in zip(xs, opt_gap):
        ax2.annotate(f"{v:.2f}%", (i + w / 2, v), ha="center", va="bottom",
                     fontsize=8, color="#534ab7")
    ax2.set_xticks(xs)
    ax2.set_xticklabels([f"K={k}" for k in ks])
    ax2.set_ylabel("makespan gap (%)")
    ax2.set_title("B. The naive earliest-available rule is near-optimal")
    ax2.legend(fontsize=8, frameon=False)
    ax2.grid(axis="y", alpha=0.25)

    fig.suptitle("Multi-drone on standard Solomon instances, with optimised "
                 "drone scheduling", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    out = os.path.join(figdir, "multidrone_std.png")
    fig.savefig(out, dpi=150)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
