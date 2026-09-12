"""Plot Schneider (2014) E-VRPTW replication route maps + vehicle-count comparison.

Provenance notes:
- BKS route geometry is NOT publicly available (only distance values from
  jmanzolli/E-VRPTW table and Adachi et al. 2022). So the "comparison" is:
  (a) route MAPS of my constructive greedy (depot / stations / customers / recharge detours),
  each annotated with my distance vs BKS distance and the gap %;
  (b) a grouped bar of my vehicle count vs BKS vehicle count across the 18 instances
  I benchmarked. This is an internal-vs-literature comparison, not a
  route-geometry overlay I cannot produce.
"""
import os, sys, csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.join(HERE, "..", "experiments")
sys.path.insert(0, EXP)
import schneider_evrptw as S

FIGDIR = os.path.join(HERE, "..", "..", "figures")
os.makedirs(FIGDIR, exist_ok=True)

# --- read BKS comparison numbers ---
cmp_path = os.path.join(EXP, "..", "results", "schneider_evrptw_bks_comparison.csv")
bks = {}
with open(cmp_path) as f:
    for row in csv.DictReader(f):
        bks[row["instance"]] = row

def coords_seq(node_by_id, ids):
    return [(node_by_id[i]["x"], node_by_id[i]["y"]) for i in ids]

def plot_routes(ax, inst, res, title):
    nbi = node_by_id = res["node_by_id"]
    depot = inst["depot"]
    # draw customers
    for c in inst["customers"]:
        ax.plot(c["x"], c["y"], "o", color="#888888", markersize=4, zorder=2)
    # draw stations
    for st in inst["stations"]:
        ax.plot(st["x"], st["y"], "^", color="#1f77b4", markersize=9, zorder=3)
    # depot
    ax.plot(depot["x"], depot["y"], "s", color="#d62728", markersize=11, zorder=4)
    # routes, color per vehicle
    nveh = len(res["routes"])
    cmap = matplotlib.colormaps["nipy_spectral"]
    for vi, trips in enumerate(res["routes"]):
        col = cmap(vi / max(nveh, 1))
        for rt in trips:
            xs, ys = zip(*coords_seq(nbi, rt))
            ax.plot(xs, ys, "-", color=col, linewidth=1.0, alpha=0.9, zorder=1)
    ax.set_title(title, fontsize=10)
    ax.set_aspect("equal", adjustable="datalim")
    ax.tick_params(labelsize=7)

# --- Figure 1: 2x2 route maps for 4 representative instances ---
pick = ["c101C5", "c103C5", "rc108C5", "c201_21"]
fig, axes = plt.subplots(2, 2, figsize=(13, 11))
for ax, name in zip(axes.flat, pick):
    inst = S.parse_instance(os.path.join(S.INST_DIR, name + ".txt"))
    res = S.solve(inst)
    c = bks.get(name)
    if c:
        gap = float(c["dist_gap_pct"])
        ttl = (f"{name}  | my dist {res['distance']:.0f} vs BKS {float(c['bks_distance']):.0f} "
               f"(gap {gap:+.1f}%)\nmy veh {res['vehicles']} vs BKS {c['bks_vehicles']}")
    else:
        ttl = f"{name}  | my dist {res['distance']:.0f}, veh {res['vehicles']}"
    plot_routes(ax, inst, res, ttl)
# legend
legend_elems = [
    Line2D([0], [0], marker="s", color="w", markerfacecolor="#d62728", markersize=11, label="Depot"),
    Line2D([0], [0], marker="^", color="w", markerfacecolor="#1f77b4", markersize=11, label="Charging station"),
    Line2D([0], [0], marker="o", color="w", markerfacecolor="#888888", markersize=8, label="Customer"),
    Line2D([0], [0], color="#555555", label="Vehicle route (color = vehicle)"),
]
fig.legend(handles=legend_elems, loc="lower center", ncol=4, fontsize=9, frameon=False)
fig.suptitle("Schneider (2014) E-VRPTW — my constructive-greedy routes\n"
             "(recharge detours show as kinks to a charging station and back)", fontsize=12)
fig.tight_layout(rect=[0, 0.04, 1, 0.96])
p1 = os.path.join(FIGDIR, "schneider_routes.png")
fig.savefig(p1, dpi=130)
plt.close(fig)
print("wrote", p1)

# --- Figure 2: vehicle count comparison (my greedy vs BKS) across 18 instances ---
inst_names = sorted(bks.keys())
my_v = [int(bks[n]["my_vehicles"]) for n in inst_names]
bk_v = [int(bks[n]["bks_vehicles"]) for n in inst_names]
y = range(len(inst_names))
fig2, ax2 = plt.subplots(figsize=(8.5, 9))
h = 0.4
ax2.barh([i + h/2 for i in y], my_v, height=h, color="#d62728", label="My greedy")
ax2.barh([i - h/2 for i in y], bk_v, height=h, color="#1f77b4", label="Schneider BKS")
ax2.set_yticks(list(y))
ax2.set_yticklabels(inst_names, fontsize=7)
ax2.invert_yaxis()
ax2.set_xlabel("Number of vehicles")
ax2.set_title("Vehicle count: my greedy vs Schneider (2014) BKS\n"
              "(BKS reachable only by an ALNS; my constructive greedy stays above it)", fontsize=10)
ax2.legend(fontsize=9)
fig2.tight_layout()
p2 = os.path.join(FIGDIR, "schneider_vehcomp.png")
fig2.savefig(p2, dpi=130)
plt.close(fig2)
print("wrote", p2)
