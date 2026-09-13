"""
Generate figures/drone_energy_mainline.png -- what the drone payload/energy
gates do to the two main-line models.

Panels:
  1. V3 (electric truck + charging + time windows), mean makespan per
     configuration at BETA = 0 (range-only control) and BETA = 0.02 (the
     drone_energy default), with the truck-only level as a dashed line;
  2. the same for the W8 K-drone FSTSP model.

A bar is labelled "n/a" when part of the instances became infeasible under the
gate; the share of feasible plans is printed under the panel title.

Reads src/results/drone_energy_mainline_summary.csv, produced by
src/experiments/drone_energy_mainline.py.
"""

import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RES = os.path.join(HERE, "src", "results", "drone_energy_mainline_summary.csv")
FIG = os.path.join(HERE, "figures", "drone_energy_mainline.png")

CONFIGS = ["greedy", "K1", "K2", "K3"]
LABELS = {"greedy": "greedy (1)", "K1": "LNS K=1", "K2": "LNS K=2",
          "K3": "LNS K=3"}
BETAS = [0.0, 0.02]
COLORS = {0.0: "#9ecae1", 0.02: "#d7301f"}


def _mean(v):
    return sum(v) / len(v) if v else 0.0


def load():
    with open(RES, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def panel(ax, rows, model, title):
    truck = _mean([float(r["truck_only_makespan"])
                   for r in rows if r["model"] == model])
    n = len(CONFIGS)
    width = 0.36
    notes = []
    for bi, beta in enumerate(BETAS):
        sub = [r for r in rows
               if r["model"] == model and float(r["beta"]) == beta]
        vals, feas = [], []
        for c in CONFIGS:
            mk = [float(r[f"{c}_makespan"]) for r in sub
                  if r[f"{c}_makespan"] != ""]
            vals.append(_mean(mk))
            feas.append(_mean([float(r[f"{c}_feas_rate"]) for r in sub]))
        xs = [i + (bi - 0.5) * width for i in range(n)]
        ax.bar(xs, vals, width, color=COLORS[beta],
               label=f"BETA = {beta:.2f}")
        for x, v, f in zip(xs, vals, feas):
            ax.annotate(f"{v:.0f}" + ("" if f > 0.999 else f"\n({f:.0%} ok)"),
                        (x, v), textcoords="offset points", xytext=(0, 3),
                        ha="center", fontsize=8)
        notes.append((beta, _mean(feas)))
    ax.axhline(truck, color="black", ls="--", lw=1.5)
    ax.annotate(f"truck only {truck:.0f}", (n - 0.55, truck),
                textcoords="offset points", xytext=(0, 4), fontsize=9)
    ax.set_xticks(range(n))
    ax.set_xticklabels([LABELS[c] for c in CONFIGS], fontsize=10)
    ax.set_ylabel("Mean makespan (time units)", fontsize=11)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.grid(True, axis="y", ls=":", alpha=0.6)
    ax.legend(fontsize=9)
    ax.margins(y=0.16)
    return notes


def main():
    rows = load()
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2))
    notes_v3 = panel(axes[0], rows, "V3",
                     "V3: electric truck + charging + time windows")
    notes_w8 = panel(axes[1], rows, "W8",
                     "W8: K parallel serial drones (FSTSP)")
    fig.suptitle("Drone payload / energy gates on the two main-line models "
                 "(mean over N = 8/12/16/20, 10 seeds)",
                 fontsize=12.5, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.9])
    os.makedirs(os.path.dirname(FIG), exist_ok=True)
    fig.savefig(FIG, dpi=130)
    print(f"[figure -> {FIG}]")
    for tag, notes in (("V3", notes_v3), ("W8", notes_w8)):
        print(tag, "mean feasibility by BETA:",
              [(b, round(f, 2)) for b, f in notes])


if __name__ == "__main__":
    main()
