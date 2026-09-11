"""
Plot figures/multidrone.png from week08_multidrone_summary.csv.

Panel A: LNS makespan per size for K = 1 / 2 / 3 drones (grouped bars).
Panel B: LNS benefit vs truck-only (%) as K grows, per size (lines).

Reads src/results/week08_multidrone_summary.csv (git-ignored; regenerate with
week08_multidrone.py first).

Run:
  python src/tools/plot_multidrone.py
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

    with open(os.path.join(res, "week08_multidrone_summary.csv"), newline="") as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: int(r["size"]))
    sizes = [r["size"] for r in rows]
    x = list(range(len(sizes)))
    Ks = [1, 2, 3]
    colors = {1: "#f0a24b", 2: "#2e7d5b", 3: "#534ab7"}
    g = lambda r, k: float(r[k])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.6))
    w = 0.26
    for i, K in enumerate(Ks):
        vals = [g(r, f"K{K}_lns_mk") for r in rows]
        ax1.bar([xx + (i - 1) * w for xx in x], vals, w,
                label=f"K={K} drones", color=colors[K])
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"N={s}" for s in sizes])
    ax1.set_ylabel("LNS makespan (completion time)")
    ax1.set_title("A. Multi-drone LNS: completion time by size")
    ax1.legend(fontsize=8, frameon=False)
    ax1.grid(axis="y", alpha=0.25)

    for K in Ks:
        vals = [g(r, f"K{K}_lns_imp_vs_truck_pct") for r in rows]
        ax2.plot(x, vals, "-o", color=colors[K], label=f"K={K} drones")
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"N={s}" for s in sizes])
    ax2.set_ylabel("LNS benefit vs truck-only (%)")
    ax2.set_title("B. Benefit vs truck-only as the drone count grows")
    ax2.legend(fontsize=8, frameon=False)
    ax2.grid(alpha=0.25)

    fig.suptitle("Breaking the single-drone limitation: K = 1/2/3 drones "
                 "(greedy + LNS, FSTSP evaluator)", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    out = os.path.join(figdir, "multidrone.png")
    fig.savefig(out, dpi=150)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
