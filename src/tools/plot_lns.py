"""
Plot the week08 LNS results: figures/lns_vs_greedy.png

Panel A: mean makespan per size for truck-only / greedy V2 / greedy+2-opt / LNS.
Panel B: improvement over the greedy V2 baseline (LNS vs greedy, 2-opt vs greedy)
         and the greedy's own improvement over truck-only.

Reads src/results/week08_lns_summary.csv (produced by week08_lns.py; the CSV is
git-ignored, so regenerate it locally with the experiment first).

Run:
  python src/tools/plot_lns.py
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

    with open(os.path.join(res, "week08_lns_summary.csv"), newline="") as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: int(r["size"]))
    sizes = [r["size"] for r in rows]
    x = range(len(sizes))
    get = lambda r, k: float(r[k])
    truck = [get(r, "truck_only_mk") for r in rows]
    greedy = [get(r, "greedy_mk") for r in rows]
    opt2 = [get(r, "opt2_mk") for r in rows]
    lns = [get(r, "lns_mk") for r in rows]
    g_imp = [get(r, "greedy_imp_vs_truck_pct") for r in rows]
    l_imp = [get(r, "lns_imp_vs_greedy_pct") for r in rows]
    o_imp = [get(r, "opt2_imp_vs_greedy_pct") for r in rows]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.6))
    w = 0.2
    xs = [i for i in x]
    ax1.bar([i - 1.5 * w for i in xs], truck, w, label="truck-only", color="#b9b9b9")
    ax1.bar([i - 0.5 * w for i in xs], greedy, w, label="V2 greedy", color="#f0a24b")
    ax1.bar([i + 0.5 * w for i in xs], opt2, w, label="V2 greedy + 2-opt", color="#7fb3e0")
    ax1.bar([i + 1.5 * w for i in xs], lns, w, label="V2 greedy + LNS", color="#2e7d5b")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels([f"N={s}" for s in sizes])
    ax1.set_ylabel("mean makespan (completion time)")
    ax1.set_title("A. Completion time by instance size (10 seeds each)")
    ax1.legend(fontsize=8, frameon=False)
    ax1.grid(axis="y", alpha=0.25)

    ax2.bar([i - 0.5 * w * 2 for i in xs], g_imp, 0.32,
            label="greedy vs truck-only", color="#f0a24b")
    ax2.bar([i + 0.5 * w * 2 for i in xs], l_imp, 0.32,
            label="LNS vs greedy", color="#2e7d5b")
    ax2.bar([i + 1.5 * w * 2 for i in xs], o_imp, 0.32,
            label="2-opt vs greedy", color="#7fb3e0")
    for i, v in zip(xs, l_imp):
        ax2.annotate(f"{v:.1f}%", (i + 0.5 * w * 2, v), ha="center",
                     va="bottom", fontsize=8, color="#2e7d5b")
    ax2.set_xticks(list(x))
    ax2.set_xticklabels([f"N={s}" for s in sizes])
    ax2.set_ylabel("improvement (%)")
    ax2.set_title("B. Where the gain comes from (vs the greedy baseline)")
    ax2.legend(fontsize=8, frameon=False)
    ax2.grid(axis="y", alpha=0.25)

    fig.suptitle("LNS improvement on the ground-air collaborative heuristic "
                 "(FSTSP evaluator, single serial drone)", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    out = os.path.join(figdir, "lns_vs_greedy.png")
    fig.savefig(out, dpi=150)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
