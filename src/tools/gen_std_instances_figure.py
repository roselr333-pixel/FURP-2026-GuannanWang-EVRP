"""
Generate figures/std_instances.png — do the synthetic conclusions transfer to
standard data?

Three panels (read from src/results/week06_std_evrp_summary.csv):
  1. V2-vs-V1 collaboration gain: standard Schneider instances (W6 capacity)
     against the synthetic reference -> the standard gain is *larger*, and the
     shrinking-with-N ordering is preserved
  2. late customers per instance, V1 vs V2 -> the drone also repairs time windows
  3. V2 feasibility under the paper's own load capacity C=200 vs the W6 default
     CAP=1000 -> the single-truck-vs-fleet mismatch shows up as capacity
"""

import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RES = os.path.join(HERE, "src", "results", "week06_std_evrp_summary.csv")
FIG = os.path.join(HERE, "figures", "std_instances.png")

rows = list(csv.DictReader(open(RES, encoding="utf-8")))
by_mode = {}
for r in rows:
    by_mode.setdefault(r["cap_mode"], {})[int(r["size"])] = r
model = by_mode["model"]
filed = by_mode["file"]
sizes = sorted(model)
ref = [float(model[n]["synthetic_ref_pct"]) for n in sizes]
gain = [float(model[n]["gain_pct"]) for n in sizes]
v1_tw = [float(model[n]["V1_tw_viol_mean"]) for n in sizes]
v2_tw = [float(model[n]["V2_tw_viol_mean"]) for n in sizes]
feas_file = [float(filed[n]["V2_feas_rate"]) * 100 for n in sizes]
feas_model = [float(model[n]["V2_feas_rate"]) * 100 for n in sizes]
labels = [f"N={n}" for n in sizes]

fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.4))

# 1) gain: standard vs synthetic reference
ax = axes[0]
x = range(len(sizes))
ax.bar([i - 0.2 for i in x], gain, width=0.4, color="#2ca02c",
       label="standard (Schneider 2014)")
ax.bar([i + 0.2 for i in x], ref, width=0.4, color="#9ecae1",
       label="synthetic reference")
for i, (g, rr) in enumerate(zip(gain, ref)):
    ax.annotate(f"{g:.0f}%", (i - 0.2, g), textcoords="offset points",
                xytext=(0, 4), ha="center", fontsize=10, fontweight="bold")
    ax.annotate(f"{rr:.0f}%", (i + 0.2, rr), textcoords="offset points",
                xytext=(0, 4), ha="center", fontsize=10)
ax.set_xticks(list(x))
ax.set_xticklabels(labels)
ax.set_ylabel("V2 shorter than V1 (%)", fontsize=11)
ax.set_xlabel("Customer count N", fontsize=11)
ax.set_title("Collaboration gain", fontsize=12, fontweight="bold")
ax.legend(fontsize=9, loc="upper right")
ax.grid(True, axis="y", ls=":", alpha=0.6)

# 2) time-window violations: V1 vs V2
ax = axes[1]
ax.plot(sizes, v1_tw, "-o", color="#d62728", lw=2, ms=8, label="V1 truck EV")
ax.plot(sizes, v2_tw, "-o", color="#2ca02c", lw=2, ms=8, label="V2 collaborative")
for xv, a, b in zip(sizes, v1_tw, v2_tw):
    ax.annotate(f"{a:.1f}", (xv, a), textcoords="offset points",
                xytext=(0, 6), ha="center", fontsize=9)
    ax.annotate(f"{b:.1f}", (xv, b), textcoords="offset points",
                xytext=(0, 6), ha="center", fontsize=9)
ax.set_xticks(sizes)
ax.set_xticklabels(labels)
ax.set_ylim(0, max(v1_tw) * 1.3)
ax.set_ylabel("Late customers per instance (mean)", fontsize=11)
ax.set_xlabel("Customer count N", fontsize=11)
ax.set_title("Time windows (60 samples per size)", fontsize=12,
             fontweight="bold")
ax.legend(fontsize=9, loc="upper left")
ax.grid(True, ls=":", alpha=0.6)

# 3) feasibility under the paper's capacity vs the W6 cap
ax = axes[2]
ax.bar([i - 0.2 for i in x], feas_file, width=0.4, color="#d62728",
       label="paper C=200 (one truck)")
ax.bar([i + 0.2 for i in x], feas_model, width=0.4, color="#4c72b0",
       label="W6 CAP=1000")
ax.set_xticks(list(x))
ax.set_xticklabels(labels)
ax.set_ylim(0, 110)
ax.set_ylabel("Capacity-feasible instances (%)", fontsize=11)
ax.set_xlabel("Customer count N", fontsize=11)
ax.set_title("Effect of the paper's fleet capacity", fontsize=12,
             fontweight="bold")
ax.legend(fontsize=9, loc="lower left")
ax.grid(True, axis="y", ls=":", alpha=0.6)

fig.suptitle("Same model on standard instances: the synthetic gain is "
             "conservative (Schneider 2014 data, 24 samples per size)",
             fontsize=12.5, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.94])
os.makedirs(os.path.dirname(FIG), exist_ok=True)
fig.savefig(FIG, dpi=130)
print(f"[figure -> {FIG}]")
print("sizes", sizes)
print("gain%", gain, "ref%", ref)
print("V1 late", v1_tw, "V2 late", v2_tw)
print("V2 feasible%: file", feas_file, "model", feas_model)
