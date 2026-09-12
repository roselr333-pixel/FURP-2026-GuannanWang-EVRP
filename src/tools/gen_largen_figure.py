"""
Generate figures/largen_scale_decay.png — the N=30/50/100 scale-boundary chart
for the ground-air collaborative EVRP-TW.

Three panels (all read from src/results/week06_largeN_summary.csv):
  1. V2 vs V1 makespan advantage (%)  -> collapses 8.6 -> 3.4 -> 0.5
  2. Drone offload rate (%)            -> collapses 11.3 -> 5.2 -> 2.6
  3. Time-window violation rate (%)     -> explodes 68.0 -> 78.0 -> 88.8

This is the scale-boundary figure for the final report: as N grows the
drone can offload a shrinking fraction of customers, so the truck dominates and
both the collaboration advantage and TW feasibility degrade.
"""

import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RES = os.path.join(HERE, "src", "results", "week06_largeN_summary.csv")
FIG = os.path.join(HERE, "figures", "largen_scale_decay.png")

sizes, imp, off_rate, tw_rate = [], [], [], []
with open(RES, newline="") as f:
    for row in csv.DictReader(f):
        n = int(row["size"])
        sizes.append(n)
        imp.append(float(row["V2_vs_V1_pct"]))
        off_rate.append(float(row["offload_rate_pct"]))
        tw_rate.append(float(row["mean_tw_viol"]) / n * 100.0)

fig, axes = plt.subplots(1, 3, figsize=(13.0, 4.3))
labels = [f"N={n}" for n in sizes]
colors = ["#2c7fb8", "#7fcdbb", "#fdae6b", "#d7301f"]


def panel(ax, y, title, ylabel, fmt, note):
    ax.plot(sizes, y, "-o", color="#1f77b4", lw=2, ms=8)
    for x, v in zip(sizes, y):
        ax.annotate(fmt.format(v), (x, v), textcoords="offset points",
                    xytext=(0, 9), ha="center", fontsize=11, fontweight="bold")
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_xlabel("Customer count N", fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_xticks(sizes)
    ax.set_xticklabels(labels)
    ax.grid(True, ls=":", alpha=0.6)
    ax.set_ylim(0, max(y) * 1.25)
    if note:
        ax.text(0.02, 0.96, note, transform=ax.transAxes, fontsize=9,
                va="top", color="#555555",
                bbox=dict(boxstyle="round", fc="#f6f6f6", ec="#cccccc"))


panel(axes[0], imp,
      "V2 vs V1 makespan advantage",
      "V2 shorter than V1 (%)", "{:.1f}%",
      "Collaboration gain collapses\nat scale")

panel(axes[1], off_rate,
      "Drone offload rate",
      "Customers served by drone (%)", "{:.1f}%",
      "Drone reaches a shrinking\nfraction of customers")

panel(axes[2], tw_rate,
      "Time-window violation rate",
      "Late customers (%)", "{:.1f}%",
      "TW feasibility breaks down\nat N=100")

fig.suptitle("Scale boundary of ground-air collaborative EVRP-TW (5 seeds, mean)",
             fontsize=13, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.95])
os.makedirs(os.path.dirname(FIG), exist_ok=True)
fig.savefig(FIG, dpi=130)
print(f"[figure -> {FIG}]")
print("sizes", sizes)
print("imp%", imp)
print("offload%", off_rate)
print("tw_viol%", tw_rate)
