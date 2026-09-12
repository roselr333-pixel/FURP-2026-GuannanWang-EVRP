"""
Generate figures/ablation_std.png -- the core ablation re-run on standard
(Solomon) instances, next to the synthetic result it is meant to check.

Panels:
  1. gain decomposition by size on the standard instances (grouped bars:
     multi-customer ability / multi-takeoff / cap3), read from
     src/results/week07_ablation_std_summary.csv;
  2. the multi-customer gain on the standard topologies vs the random cloud
     (lines), read from the same file and week07_ablation_summary.csv.

The point of the figure is the comparison: if "multi-customer sorties are the
main gain source" were an artifact of the random geometry, the two lines in
panel 2 would disagree.
"""

import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RES = os.path.join(HERE, "src", "results")
FIG = os.path.join(HERE, "figures", "ablation_std.png")


def _read(name):
    path = os.path.join(RES, name)
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


std = sorted(_read("week07_ablation_std_summary.csv"), key=lambda r: int(r["size"]))
syn = {int(r["size"]): r for r in _read("week07_ablation_summary.csv")}
sizes = [int(r["size"]) for r in std]
labels = [f"N={n}" for n in sizes]
x = range(len(sizes))
w = 0.26

fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.6))

ax = axes[0]
ax.bar([i - w for i in x],
       [float(r["gain_multicust_pp"]) for r in std], w,
       label="multi-customer", color="#2c7fb8")
ax.bar(list(x),
       [float(r["gain_notakeoff_pp"]) for r in std], w,
       label="multi-takeoff", color="#7fcdbb")
ax.bar([i + w for i in x],
       [float(r["gain_cap3_pp"]) for r in std], w,
       label="cap3", color="#fdae6b")
for i, r in enumerate(std):
    ax.annotate(f"{float(r['gain_multicust_pp']):.1f}", (i - w, float(r["gain_multicust_pp"])),
                textcoords="offset points", xytext=(0, 4), ha="center", fontsize=9)
ax.set_xticks(list(x))
ax.set_xticklabels(labels)
ax.set_ylabel("Gain vs truck-only (pp)", fontsize=11)
ax.set_title("Gain decomposition, standard instances", fontsize=12, fontweight="bold")
ax.grid(True, axis="y", ls=":", alpha=0.6)
ax.legend(fontsize=9)

ax = axes[1]
ax.plot(list(x), [float(r["gain_multicust_pp"]) for r in std], "-o",
        color="#2c7fb8", lw=2, ms=7, label="standard (Solomon topology)")
if syn:
    ax.plot(list(x), [float(syn[n]["gain_multicust_pp"]) for n in sizes], "--s",
            color="#d7301f", lw=2, ms=7, label="synthetic random geometry")
ax.set_xticks(list(x))
ax.set_xticklabels(labels)
ax.set_ylabel("Multi-customer gain (pp)", fontsize=11)
ax.set_title("Main gain source on both geometries", fontsize=12, fontweight="bold")
ax.grid(True, ls=":", alpha=0.6)
ax.legend(fontsize=9)

fig.suptitle("Core ablation on standard (Solomon) instances (48 instances, "
             "same heuristic and evaluator as the synthetic run)",
             fontsize=12.5, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.93])
os.makedirs(os.path.dirname(FIG), exist_ok=True)
fig.savefig(FIG, dpi=130)
print(f"[figure -> {FIG}]")
print("sizes", sizes)
print("multi-customer", [r["gain_multicust_pp"] for r in std])
print("multi-takeoff", [r["gain_notakeoff_pp"] for r in std])
print("cap3", [r["gain_cap3_pp"] for r in std])
