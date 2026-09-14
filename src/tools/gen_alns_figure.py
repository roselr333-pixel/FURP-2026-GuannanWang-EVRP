"""
Figure for the ALNS on the physical FSTSP model.

Left panel : per size, the mean makespan of the clean greedy, the existing LNS and
             the ALNS, with the best feasible plan CP-SAT found as a reference
             line (that is the bar the search side has to chase).
Right panel: what the ALNS gained over the LNS, and the adaptivity ablation
             (same budget and seed with the operator weights frozen).

Reads src/results/week08_alns_summary.csv and _raw.csv; writes
figures/alns_fstsp.png.

Run:
  python src/tools/gen_alns_figure.py
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
    with open(os.path.join(RES, "week08_alns_summary.csv"),
              newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    sizes = [int(r["size"]) for r in rows]
    greedy = [float(r["greedy_mk"]) for r in rows]
    lns = [float(r["lns_mk"]) for r in rows]
    alns = [float(r["alns_mk"]) for r in rows]
    cp = [float(r["cp_sat_primal_mk"]) if r["cp_sat_primal_mk"] != "" else None
          for r in rows]
    imp = [float(r["alns_imp_vs_lns_mean_pct"]) for r in rows]
    adapt = [float(r["adaptive_vs_fixed_mean_pct"]) for r in rows]

    x = list(range(len(sizes)))
    width = 0.26
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 4.6))

    ax = axes[0]
    ax.bar([i - width for i in x], greedy, width, label="greedy (V2)",
           color="#D85A30")
    ax.bar(x, lns, width, label="existing LNS (week08_lns)", color="#8C8C8C")
    ax.bar([i + width for i in x], alns, width, label="ALNS (this module)",
           color="#1D9E75")
    for i, c in enumerate(cp):
        if c is not None:
            ax.hlines(c, i - 0.45, i + 0.45, color="#2C7FB8", lw=2, ls="--")
    if any(c is not None for c in cp):
        ax.plot([], [], "--", color="#2C7FB8", lw=2,
                label="CP-SAT best feasible plan")
    for i, (g, l, a) in enumerate(zip(greedy, lns, alns)):
        for xx, v in ((i - width, g), (i, l), (i + width, a)):
            ax.annotate(f"{v:.0f}", (xx, v), textcoords="offset points",
                        xytext=(0, 3), ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"n={s}" for s in sizes])
    ax.set_ylabel("mean makespan (physical FSTSP)", fontsize=10)
    ax.set_title("Search quality against the CP-SAT primal", fontsize=11,
                 fontweight="bold")
    ax.legend(frameon=False, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25)

    ax = axes[1]
    ax.bar([i - width / 2 for i in x], imp, width, color="#1D9E75",
           label="ALNS vs LNS")
    ax.bar([i + width / 2 for i in x], adapt, width, color="#9ECAE1",
           label="adaptive vs fixed weights")
    for i, (a, b) in enumerate(zip(imp, adapt)):
        ax.annotate(f"{a:+.1f}%", (i - width / 2, a), textcoords="offset points",
                    xytext=(0, 3), ha="center", fontsize=9)
        ax.annotate(f"{b:+.2f}%", (i + width / 2, b),
                    textcoords="offset points", xytext=(0, 3), ha="center",
                    fontsize=8)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"n={s}" for s in sizes])
    ax.set_ylabel("improvement over the LNS (%)", fontsize=10)
    ax.set_title("What the ALNS adds, and what the adaptivity adds", fontsize=11,
                 fontweight="bold")
    ax.legend(frameon=False, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25)

    fig.suptitle("ALNS on the physical FSTSP model (5 seeds per size)",
                 fontsize=12, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    os.makedirs(FIG, exist_ok=True)
    out = os.path.join(FIG, "alns_fstsp.png")
    fig.savefig(out, dpi=150)
    print(f"[figure -> {out}]")
    for s, g, l, a, c, i, d in zip(sizes, greedy, lns, alns, cp, imp, adapt):
        cp_txt = f"{c:.1f}" if c is not None else "-"
        print(f"  n={s:2d}: greedy {g:7.1f} | LNS {l:7.1f} | ALNS {a:7.1f} "
              f"| CP-SAT {cp_txt:>7} | vs LNS {i:+.2f}% | adaptive {d:+.2f}%")


if __name__ == "__main__":
    main()
