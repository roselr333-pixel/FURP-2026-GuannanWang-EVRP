"""
Generate figures/capacity_binding.png — the truck-capacity study.

Three panels (all read from src/results/week06_capacity_raw.csv):
  1. mean total demand per size vs the three caps -> where CAP starts to bind
  2. capacity-feasibility rate (truck load <= cap) for V1 and V2 -> V2 can only
     rescue the cases whose overload one serial drone can actually remove
  3. demand left on the truck at the declared CAP=1000 -> the repair ceiling

Capacity only: energy feasibility is a separate gate (the N=100 truck route is
already energy-infeasible in the W6 line), so this figure deliberately does not
mix the two.
"""

import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RES = os.path.join(HERE, "src", "results", "week06_capacity_raw.csv")
FIG = os.path.join(HERE, "figures", "capacity_binding.png")

CAPS = [1000, 600, 400]

rows = []
with open(RES, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        rows.append({k: (float(v) if v not in ("", None) else float("nan"))
                     for k, v in row.items()})
sizes = sorted({int(r["size"]) for r in rows})
labels = [f"N={n}" for n in sizes]

fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.4))

# 1) demand vs caps
ax = axes[0]
demand = [sum(r["total_demand"] for r in rows if int(r["size"]) == n) /
          len([r for r in rows if int(r["size"]) == n]) for n in sizes]
ax.bar(range(len(sizes)), demand, color="#9ecae1", edgecolor="#4a7fa5")
for cap, style in zip(CAPS, ["-", "--", ":"]):
    ax.axhline(cap, color="#d62728", ls=style, lw=1.6,
               label=f"cap={cap}" + (" (declared)" if cap == 1000 else ""))
ax.set_xticks(range(len(sizes)))
ax.set_xticklabels(labels)
ax.set_title("Demand vs capacity", fontsize=12, fontweight="bold")
ax.set_ylabel("Total customer demand", fontsize=11)
ax.set_xlabel("Customer count N", fontsize=11)
ax.legend(fontsize=8, loc="upper left")
ax.grid(True, axis="y", ls=":", alpha=0.6)

# 2) capacity feasibility (truck load <= cap), capacity only
ax = axes[1]
for cap, color, marker in zip(CAPS, ["#1f77b4", "#ff7f0e", "#d62728"], ["o", "s", "^"]):
    y = []
    for n in sizes:
        sub = [r for r in rows if int(r["size"]) == n and r["cap"] == cap]
        ok = sum(1 for r in sub if r["V2_truck_load"] <= r["cap"])
        y.append(ok / len(sub) * 100.0)
    ax.plot(sizes, y, marker=marker, color=color, lw=2, ms=7,
            label=f"V2, cap={cap}")
ax.set_ylim(-5, 105)
ax.set_xticks(sizes)
ax.set_xticklabels(labels)
ax.set_title("Type capacity-feasible after repair", fontsize=12, fontweight="bold")
ax.set_ylabel("Instances with truck load <= cap (%)", fontsize=11)
ax.set_xlabel("Customer count N", fontsize=11)
ax.legend(fontsize=9, loc="lower left")
ax.grid(True, ls=":", alpha=0.6)

# 3) repair ceiling at the declared cap
ax = axes[2]
ratio = []
for n in sizes:
    sub = [r for r in rows if int(r["size"]) == n and r["cap"] == 1000]
    # ratio of means (same convention as the study's summary table)
    ratio.append(sum(r["V2_truck_load"] for r in sub)
                 / sum(r["total_demand"] for r in sub) * 100.0)
ax.plot(sizes, ratio, "-o", color="#8c564b", lw=2, ms=8)
for x, v in zip(sizes, ratio):
    ax.annotate(f"{v:.0f}%", (x, v), textcoords="offset points",
                xytext=(0, 9), ha="center", fontsize=10, fontweight="bold")
ax.axhline(100, color="#555555", ls=":", lw=1.2)
ax.set_ylim(55, 108)
ax.set_xticks(sizes)
ax.set_xticklabels(labels)
ax.set_title("Demand left on the truck (CAP=1000)", fontsize=12, fontweight="bold")
ax.set_ylabel("Truck load / total demand (%)", fontsize=11)
ax.set_xlabel("Customer count N", fontsize=11)
ax.text(0.03, 0.06, "one serial drone removes only\na modest share of demand",
        transform=ax.transAxes, fontsize=9, color="#555555",
        bbox=dict(boxstyle="round", fc="#f6f6f6", ec="#cccccc"))
ax.grid(True, ls=":", alpha=0.6)

fig.suptitle("Truck capacity study: is the declared CAP binding? (5 seeds, mean)",
             fontsize=13, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.94])
os.makedirs(os.path.dirname(FIG), exist_ok=True)
fig.savefig(FIG, dpi=130)
print(f"[figure -> {FIG}]")
print("sizes", sizes)
print("demand", [round(d, 1) for d in demand])
print("V2 capacity-feasible % @cap1000",
      [round(100.0 * sum(1 for r in rows if int(r["size"]) == n
                         and r["cap"] == 1000 and r["V2_truck_load"] <= r["cap"])
             / len([r for r in rows if int(r["size"]) == n and r["cap"] == 1000]), 1)
       for n in sizes])
print("V2 load %", [round(v, 1) for v in ratio])
