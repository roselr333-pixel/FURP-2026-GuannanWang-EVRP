"""
Generate figures/drone_energy.png -- what a payload-aware drone energy model does
to the core ablation.

Panels:
  1. the multi-customer gain (percentage points) against the payload coefficient
     BETA, for the synthetic and standard instance sets;
  2. the feasibility rate under the energy model: the published (energy-unaware)
     heuristic against my energy-aware greedy.

Both read src/results/drone_energy_summary.csv, produced by
src/experiments/drone_energy_ablation.py.
"""

import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RES = os.path.join(HERE, "src", "results", "drone_energy_summary.csv")
FIG = os.path.join(HERE, "figures", "drone_energy.png")


def _mean(v):
    return sum(v) / len(v) if v else 0.0


with open(RES, newline="") as f:
    rows = list(csv.DictReader(f))

betas = sorted({float(r["beta"]) for r in rows})
sets = ["synthetic", "standard"]


def series(iset, col):
    out = []
    for b in betas:
        sub = [r for r in rows
               if r["instance_set"] == iset and float(r["beta"]) == b]
        out.append(_mean([float(r[col]) for r in sub]))
    return out


fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.9))
colors = {"synthetic": "#d7301f", "standard": "#2c7fb8"}

ax = axes[0]
for iset in sets:
    y = series(iset, "gain_multicust_pp")
    ax.plot(betas, y, "-o", color=colors[iset], lw=2, ms=7, label=iset)
    for b, v in zip(betas, y):
        ax.annotate(f"{v:+.1f}", (b, v), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=9)
ax.set_xlabel("Payload coefficient BETA (0 = the old range-only model)",
              fontsize=11)
ax.set_ylabel("Multi-customer gain (percentage points)", fontsize=11)
ax.set_title("Multi-customer advantage vs payload penalty",
             fontsize=12, fontweight="bold")
ax.set_xticks(betas)
ax.grid(True, ls=":", alpha=0.6)
ax.legend(fontsize=9)

ax = axes[1]
for iset in sets:
    ax.plot(betas, series(iset, "published_feas_rate"), "--s",
            color=colors[iset], lw=2, ms=7,
            label=f"published M&C (energy-unaware), {iset}")
ax.plot(betas, series("synthetic", "v2_feas_rate"), "-o", color="#2c7fb8",
        lw=2, ms=7, label="my greedy, synthetic")
ax.plot(betas, series("standard", "v2_feas_rate"), "-^", color="#d7301f",
        lw=2, ms=7, label="my greedy, standard")
ax.set_xlabel("Payload coefficient BETA", fontsize=11)
ax.set_ylabel("Share of plans that are energy-feasible", fontsize=11)
ax.set_title("Energy-awareness decides feasibility", fontsize=12,
             fontweight="bold")
ax.set_ylim(0, 1.08)
ax.set_xticks(betas)
ax.grid(True, ls=":", alpha=0.6)
ax.legend(fontsize=8)

fig.suptitle("Drone energy / payload model: effect on the core ablation "
             "(mean over sizes, 40 synthetic + 48 standard instances)",
             fontsize=12.5, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.88])
os.makedirs(os.path.dirname(FIG), exist_ok=True)
fig.savefig(FIG, dpi=130)
print(f"[figure -> {FIG}]")
for iset in sets:
    print(iset, "multi-customer", [round(v, 1) for v in
                                   series(iset, "gain_multicust_pp")])
    print(iset, "published feas", [round(v, 2) for v in
                                   series(iset, "published_feas_rate")])
