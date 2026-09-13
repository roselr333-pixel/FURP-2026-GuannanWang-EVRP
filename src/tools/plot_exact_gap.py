"""
Figure for the exact optimality gap: my greedy and the LNS against the CP-SAT
exact optimum, per size. Reads src/results/week08_exact_gap_summary.csv and
writes figures/exact_gap.png.

Run:
  python src/tools/plot_exact_gap.py
"""

import os
import csv

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RES = os.path.join(HERE, "src", "results")
FIG = os.path.join(HERE, "figures")


def main():
    path = os.path.join(RES, "week08_exact_gap_summary.csv")
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    sizes = [r["size"] for r in rows]
    greedy = [float(r["greedy_gap_mean_pct"]) for r in rows]
    lns = [float(r["lns_gap_mean_pct"]) for r in rows]
    proven = [int(r["n_opt_proven"]) for r in rows]
    total = [int(r["n_instances"]) for r in rows]

    x = range(len(sizes))
    width = 0.38
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    b1 = ax.bar([i - width / 2 for i in x], greedy, width,
                label="greedy (V2, physical)", color="#D85A30")
    b2 = ax.bar([i + width / 2 for i in x], lns, width,
                label="greedy + LNS", color="#1D9E75")
    for bars in (b1, b2):
        for bar in bars:
            h = bar.get_height()
            ax.annotate(f"{h:.1f}%", (bar.get_x() + bar.get_width() / 2, h),
                        ha="center", va="bottom", fontsize=9)
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"n={s}\n(opt proved {p}/{t})"
                        for s, p, t in zip(sizes, proven, total)])
    ax.set_ylabel("gap to exact optimum (%)")
    ax.set_title("Distance from the CP-SAT exact optimum")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25)
    os.makedirs(FIG, exist_ok=True)
    out = os.path.join(FIG, "exact_gap.png")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(f"[figure -> {out}]")


if __name__ == "__main__":
    main()
