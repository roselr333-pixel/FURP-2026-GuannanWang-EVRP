"""
Week 6 (extension) — Parameter sensitivity study for the ground-air EVRP-TW.

Depth upgrade (2026-09-10): every parameter level is now evaluated over 5
instance seeds and reported as MEAN ± STD, with error bars in the figures.
This turns "a single number per level" into a statistically-backed statement
about how the truck-drone SYNERGY BENEFIT
    benefit = (dist_V1_truck_EV - dist_V2_collab) / dist_V1_truck_EV * 100%
responds to the physical parameters. The point is not more numbers — it is to
characterise the REGIME where collaboration pays off, and to show that the
finding is stable across random instances.

Reuses the existing greedy framework (week06 / week07 modules) so the numbers
stay consistent with the ablation study. Synthetic instances via make_instance.

Paths are resolved relative to this file, so the script runs from any CWD.

Outputs:
  figures/sensitivity_panels.png   (4 panels, mean±std)
  src/results/week06_sensitivity.csv            (raw sweep table with std)
"""
import os
import csv
import statistics
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import week06_ground_air_evrp_tw as w6
import week07_improvement_ablation as w7
import week07_fstsp_repro as f7

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SEEDS = [20260910, 20260911, 20260912, 20260913, 20260914]
N_BASE = 12
FIG_DIR = os.path.join(REPO, "figures")
os.makedirs(FIG_DIR, exist_ok=True)


def evaluate(inst, drone_range=None, max_cust=2):
    """Return (v1_dist, v2_dist, v2_makespan, n_offloaded) for one instance."""
    # drone_range may be carried on the instance (used by the R sweep below);
    # otherwise my_v2_param falls back to the module default R_D.
    rd = drone_range if drone_range is not None else inst.get("drone_range")
    custs = list(inst["customers"].keys())
    v1 = w6.truck_ev_route(inst, custs, allow_recharge=True, q=inst["Q"])
    v1_dist = v1["total_dist"]
    route, trips, off = w7.my_v2_param(inst, max_cust=max_cust,
                                       multi_takeoff=True, drone_range=rd)
    v2_dist = w6.route_distance(inst, route)
    v2_mk = f7.fstsp_makespan(inst, route, trips)
    return v1_dist, v2_dist, v2_mk, len(off)


def benefit(v1_dist, v2_dist):
    return (v1_dist - v2_dist) / v1_dist * 100.0 if v1_dist > 0 else 0.0


def sweep(param_fn, values):
    """param_fn(value, seed) -> inst ; returns list of
    (value, mean_benefit, std_benefit, mean_v1, mean_v2)."""
    rows = []
    for v in values:
        bs, d1, d2 = [], [], []
        for s in SEEDS:
            inst = param_fn(v, s)
            v1, v2, _, _ = evaluate(inst)
            bs.append(benefit(v1, v2))
            d1.append(v1)
            d2.append(v2)
        rows.append((v, sum(bs) / len(bs), statistics.pstdev(bs),
                     sum(d1) / len(d1), sum(d2) / len(d2)))
    return rows


# ---- sweep definitions -----------------------------------------------------
def mk_q(q, seed):
    return w6.make_instance(N_BASE, seed=seed, q=q)


def mk_range(r, seed):
    # store the varying endurance on the instance so evaluate() (and the V2
    # model) actually honours it; previously `r` was ignored -> flat sweep.
    inst = w6.make_instance(N_BASE, seed=seed)
    inst["drone_range"] = r
    return inst


def mk_n(n, seed):
    return w6.make_instance(n, seed=seed)


def main():
    results = {}

    # (1) battery capacity Q
    results["Q_battery"] = sweep(lambda v, s: mk_q(v, s),
                                 [120, 180, 250, 350, 500])

    # (2) drone flight range R (endurance proxy)
    results["R_drone_range"] = sweep(lambda v, s: mk_range(v, s),
                                     [60, 90, 120, 160, 200])

    # (3) max customers per drone sortie K
    results["K_max_cust"] = \
        [(k,
          sum(benefit(*evaluate(w6.make_instance(N_BASE, seed=s), max_cust=k)[0:2])
              for s in SEEDS) / len(SEEDS),
          statistics.pstdev([benefit(*evaluate(w6.make_instance(N_BASE, seed=s),
                                               max_cust=k)[0:2]) for s in SEEDS]),
          sum(evaluate(w6.make_instance(N_BASE, seed=s), max_cust=k)[0]
              for s in SEEDS) / len(SEEDS),
          sum(evaluate(w6.make_instance(N_BASE, seed=s), max_cust=k)[1]
              for s in SEEDS) / len(SEEDS))
         for k in [1, 2, 3]]

    # (4) customer scale N  (cap at 30 here; n=50 decay already in week06_largeN)
    results["N_scale"] = sweep(lambda v, s: mk_n(v, s),
                               [8, 12, 16, 20, 30])

    # ---- write CSV ----
    csv_path = os.path.join(REPO, "src", "results", "week06_sensitivity.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["param", "value", "benefit_pct", "benefit_std_pct",
                    "v1_dist_mean", "v2_dist_mean"])
        for p, rows in results.items():
            for v, b, sd, d1, d2 in rows:
                w.writerow([p, v, round(b, 2), round(sd, 2),
                            round(d1, 1), round(d2, 1)])

    # ---- figures (4 panels, mean ± std) ----
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    specs = [
        ("Q_battery", axes[0, 0], "Battery capacity Q", "benefit %"),
        ("R_drone_range", axes[0, 1], "Drone range R", "benefit %"),
        ("K_max_cust", axes[1, 0], "Max customers / sortie K", "benefit %"),
        ("N_scale", axes[1, 1], "Customers N (scale)", "benefit %"),
    ]
    for key, ax, xlab, ylab in specs:
        xs = [r[0] for r in results[key]]
        ys = [r[1] for r in results[key]]
        errs = [r[2] for r in results[key]]
        ax.errorbar(xs, ys, yerr=errs, fmt="o-", color="#2c7fb8",
                    linewidth=2, markersize=6, capsize=4, ecolor="#7fcdbb")
        ax.set_xlabel(xlab)
        ax.set_ylabel(ylab)
        ax.set_title(f"Synergy benefit vs {xlab} (mean±std, 5 seeds)")
        ax.grid(alpha=0.3)
    fig.suptitle("Ground-air EVRP-TW — parameter sensitivity (5 seeds, n=12 "
                 "except scale sweep)", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig_path = os.path.join(FIG_DIR, "sensitivity_panels.png")
    fig.savefig(fig_path, dpi=130)
    print(f"wrote {fig_path}")
    print(f"wrote {csv_path}")
    for p, rows in results.items():
        print(f"  {p}: " + ", ".join(f"{v}->{b:.1f}±{sd:.1f}%" for v, b, sd, _, _ in rows))


if __name__ == "__main__":
    main()
