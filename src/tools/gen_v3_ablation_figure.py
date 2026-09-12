"""
Generate figures/v3_ablation.png -- the core ablation on the V3 model
(electric truck + drone + charging + time windows).

Panels:
  1. improvement over the truck-only EV anchor for the four configurations, by
     size;
  2. the gain decomposition (multi-customer / multi-takeoff / cap3) in percentage
     points.

Both panels read src/results/v3_ablation_summary.csv, produced by
src/experiments/v3_ablation.py.
"""

import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RES = os.path.join(HERE, "src", "results", "v3_ablation_summary.csv")
FIG = os.path.join(HERE, "figures", "v3_ablation.png")

CH = {1: "#2c7fb8", 2: "#7fcdbb", 3: "#fdae6b", 4: "#d7301f"}

with open(RES, newline="") as f:
    rows = sorted(csv.DictReader(f), key=lambda r: int(r["size"]))

sizes = [int(r["size"]) for r in rows]
labels = [f"N={n}" for n in sizes]
x = range(len(sizes))
w = 0.2

fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.6))

ax = axes[0]
for k, c in enumerate(["cap1", "v2", "notakeoff", "cap3"]):
    ax.bar([i + (k - 1.5) * w for i in x],
           [float(r[f"{c}_imp_vs_V1_pct"]) for r in rows], w,
           label=c, color=CH[k + 1])
ax.set_xticks(list(x))
ax.set_xticklabels(labels)
ax.set_ylabel("Improvement over truck-only EV (%)", fontsize=11)
ax.set_title("V3 configurations vs the truck-only EV anchor",
             fontsize=12, fontweight="bold")
ax.grid(True, axis="y", ls=":", alpha=0.6)
ax.legend(fontsize=9)

ax = axes[1]
W = 0.26
ax.bar([i - W for i in x],
       [float(r["gain_multicust_pp"]) for r in rows], W,
       label="multi-customer (v2-cap1)", color="#2c7fb8")
ax.bar(list(x),
       [float(r["gain_notakeoff_pp"]) for r in rows], W,
       label="stop reuse (v2-notakeoff)", color="#7fcdbb")
ax.bar([i + W for i in x],
       [float(r["gain_cap3_pp"]) for r in rows], W,
       label="cap3 (cap3-v2)", color="#fdae6b")
ax.axhline(0.0, color="#444444", lw=0.8)
for i, r in enumerate(rows):
    ax.annotate(f"{float(r['gain_multicust_pp']):+.1f}",
                (i - W, float(r["gain_multicust_pp"])),
                textcoords="offset points", xytext=(0, 4), ha="center",
                fontsize=9)
ax.set_xticks(list(x))
ax.set_xticklabels(labels)
ax.set_ylabel("Gain (percentage points)", fontsize=11)
ax.set_title("Gain decomposition under EV + time windows",
             fontsize=12, fontweight="bold")
ax.grid(True, axis="y", ls=":", alpha=0.6)
ax.legend(fontsize=9)

fig.suptitle("Core ablation on the V3 model (electric truck + drone + charging "
             "+ time windows, 10 seeds)", fontsize=12.5, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.93])
os.makedirs(os.path.dirname(FIG), exist_ok=True)
fig.savefig(FIG, dpi=130)
print(f"[figure -> {FIG}]")
print("sizes", sizes)
print("multi-customer", [r["gain_multicust_pp"] for r in rows])
print("multi-takeoff", [r["gain_notakeoff_pp"] for r in rows])
print("cap3", [r["gain_cap3_pp"] for r in rows])
