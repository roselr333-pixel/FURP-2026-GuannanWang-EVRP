"""
Figure for the exact optimality gap.

Left panel : my greedy and the LNS against the best plan CP-SAT found, per size;
             the n=8 bar is against the proven optimum, the larger sizes are
             against the best feasible plan (so those bars are lower bounds on the
             true gap).
Right panel: the same runs' primal (best feasible plan) against the dual bound
             CP-SAT could certify, per size -- this is where the boundary is: the
             relaxation stays one order of magnitude below the incumbent, so
             optimality cannot be proved beyond n=8.

Reads src/results/week08_exact_gap_summary.csv and _raw.csv; writes
figures/exact_gap.png.

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


def _mean(v):
    return sum(v) / len(v) if v else 0.0


def main():
    with open(os.path.join(RES, "week08_exact_gap_summary.csv"),
              newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    with open(os.path.join(RES, "week08_exact_gap_raw.csv"),
              newline="", encoding="utf-8") as f:
        raw = list(csv.DictReader(f))

    sizes = [int(r["size"]) for r in rows]
    greedy = [float(r["greedy_gap_mean_pct"]) for r in rows]
    lns = [float(r["lns_gap_mean_pct"]) for r in rows]
    proven = [int(r["n_opt_proven"]) for r in rows]
    total = [int(r["n_instances"]) for r in rows]
    primal = [_mean([float(x["opt"]) for x in raw
                     if int(x["size"]) == n and x["opt"] != ""])
              for n in sizes]
    dual = [_mean([float(x["opt_bound"]) for x in raw
                   if int(x["size"]) == n and x["opt_bound"] != ""])
            for n in sizes]

    x = range(len(sizes))
    width = 0.38
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.4))

    ax = axes[0]
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
    ax.set_xticklabels([f"n={n}\n" + (f"optimum {p}/{t}" if p else "best found")
                        for n, p, t in zip(sizes, proven, total)], fontsize=9)
    ax.set_ylabel("gap to the best plan found (%)", fontsize=10)
    ax.set_title("Heuristic gap (n=8: proven optimum)", fontsize=11,
                 fontweight="bold")
    ax.legend(frameon=False, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25)

    ax = axes[1]
    ax.plot(list(x), primal, "-o", color="#1D9E75", lw=2, ms=7,
            label="best feasible plan (primal)")
    ax.plot(list(x), dual, "--s", color="#7A7A7A", lw=2, ms=7,
            label="certified dual bound")
    for i, (p, d) in enumerate(zip(primal, dual)):
        ax.annotate(f"{p:.0f}", (i, p), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=9)
        ax.annotate("0" if d < 1e-6 else f"{d:.0f}", (i, max(d, 1.0)),
                    textcoords="offset points", xytext=(0, -14), ha="center",
                    fontsize=9, color="#555555")
    ax.set_yscale("log")
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"n={n}" for n in sizes])
    ax.set_ylabel("makespan (log scale)", fontsize=10)
    ax.set_title("Where the proof stops: primal vs dual bound", fontsize=11,
                 fontweight="bold")
    ax.legend(frameon=False, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", which="both", alpha=0.2)

    fig.suptitle("CP-SAT exact model, warm-started (5 seeds per size)",
                 fontsize=12, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    os.makedirs(FIG, exist_ok=True)
    out = os.path.join(FIG, "exact_gap.png")
    fig.savefig(out, dpi=150)
    print(f"[figure -> {out}]")
    for n, p, d, g, l in zip(sizes, primal, dual, greedy, lns):
        print(f"  n={n:2d}: primal {p:7.1f} | dual {d:7.1f} | "
              f"greedy {g:6.1f}% | LNS {l:6.1f}%")


if __name__ == "__main__":
    main()
