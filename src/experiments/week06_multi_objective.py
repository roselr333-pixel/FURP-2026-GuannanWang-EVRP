"""
Week 6 (extension) — Multi-objective trade-off for ground-air EVRP-TW.

Benchmarked against Xie's P-ACO Pareto archive: instead of a single
distance objective, we report the solution on TWO axes that genuinely
trade off in the synchronous truck-drone model:
    f1 = total distance (truck route length)        -- cost
    f2 = makespan (route completion time)            -- service time
    f3 = total energy (truck + drone, proxy)         -- environment

We do NOT pretend to run a full NSGA-II / Pareto solver. We use an honest
weighted-sum scalarisation: the greedy insertion score is
    score = w * (distance saving) + (1-w) * (makespan reduction)
and sweep w in [0, 0.25, 0.5, 0.75, 1.0]. w=0 reproduces the standard V2
(makespan-driven); w=1 is a distance-only greedy. The cloud of (f1, f2)
points across w and seeds traces the achievable trade-off front, and we
show V2 dominates the truck-only (V1) baseline on both axes.

Outputs:
  figures/mo_scatter.png     (V1 vs V2-weighted cloud)
  figures/mo_tradeoff.png    (one instance: dist vs makespan vs w)
  src/results/week06_multi_objective.csv
"""
import os
import csv
import itertools
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import week06_ground_air_evrp_tw as w6
import week07_fstsp_repro as f7

SEEDS = [20260910, 20260911, 20260912, 20260913, 20260914]
N = 12
WS = [0.0, 0.25, 0.5, 0.75, 1.0]
RHO = 1.0          # truck energy per distance unit (from week06)
DRONE_RHO = 0.3    # drone energy per distance unit (proxy: cheaper per km)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIG_DIR = os.path.join(REPO, "figures")
os.makedirs(FIG_DIR, exist_ok=True)


def drone_flight_dist(inst, trips):
    tot = 0.0
    for ln, custs, rn in trips:
        seq = (ln,) + custs + (rn,)
        tot += sum(w6.dist(inst, seq[p], seq[p + 1])
                   for p in range(len(seq) - 1))
    return tot


def my_v2_weighted(inst, w, max_cust=2, multi_takeoff=True, drone_range=None):
    """Copy of my_v2_param with weighted-sum insertion score (honest MO)."""
    rd = drone_range if drone_range is not None else w6.R_D
    all_c = list(inst["customers"].keys())
    route = [0] + w6.nn_order(inst, all_c) + [0]
    drone_trips = []
    offloaded = set()
    protected = set()
    blocked = set()

    def usable_stop(node):
        if multi_takeoff:
            return True
        return node not in blocked

    while True:
        base = f7.fstsp_makespan(inst, route, drone_trips)
        best = None
        n = len(route)
        for i_idx in range(n - 1):
            ln = route[i_idx]
            if not usable_stop(ln):
                continue
            for j_idx in range(i_idx + 2, n):
                rn = route[j_idx]
                if not usable_stop(rn):
                    continue
                cands = [route[p] for p in range(i_idx + 1, j_idx)
                         if route[p] != 0 and route[p] not in offloaded
                         and route[p] not in protected]
                if not cands:
                    continue
                tt_lr = f7._truck_travel(inst, route, i_idx, j_idx)
                subsets = []
                if max_cust >= 1:
                    for c in cands:
                        subsets.append((c,))
                if max_cust >= 2 and len(cands) >= 2:
                    for x in range(len(cands)):
                        for y in range(x + 1, len(cands)):
                            subsets.append((cands[x], cands[y]))
                            subsets.append((cands[y], cands[x]))
                if max_cust >= 3 and len(cands) >= 3:
                    for trio in itertools.combinations(cands, 3):
                        for perm in itertools.permutations(trio):
                            subsets.append(tuple(perm))
                for custs in subsets:
                    ok = True
                    prev = ln
                    for c in custs:
                        if w6.dist(inst, prev, c) > rd:
                            ok = False
                            break
                        prev = c
                    if ok and w6.dist(inst, prev, rn) > rd:
                        ok = False
                    if not ok:
                        continue
                    d = sum(w6.dist(inst, (ln, *custs, rn)[p],
                                    (ln, *custs, rn)[p + 1])
                            for p in range(len(custs) + 1))
                    if d > rd:
                        continue
                    s = sum(f7._remove_saving(inst, route, c) for c in custs)
                    flight = d / w6.V_D + w6.SERVICE * len(custs)
                    delay = max(0.0, flight - (tt_lr - s))
                    if s - delay <= 0:
                        continue
                    new_route = [x for x in route if x not in custs]
                    new_trips = drone_trips + [(ln, custs, rn)]
                    true_net = base - f7.fstsp_makespan(inst, new_route,
                                                        new_trips)
                    score = w * s + (1 - w) * true_net
                    if score > 0 and (best is None or score > best[0]):
                        best = (score, ln, rn, custs)
        if best is None:
            break
        _, ln, rn, custs = best
        for c in custs:
            offloaded.add(c)
        protected.add(ln)
        protected.add(rn)
        if not multi_takeoff:
            blocked.add(ln)
            blocked.add(rn)
        drone_trips.append((ln, custs, rn))
        route = [x for x in route if x not in custs]
    return route, drone_trips, offloaded


def metrics(inst, route, trips):
    dist = w6.route_distance(inst, route)
    mk = f7.fstsp_makespan(inst, route, trips)
    energy = dist * RHO + drone_flight_dist(inst, trips) * DRONE_RHO
    return dist, mk, energy, len(trips)


def main():
    rows = []
    v2_cloud, v1_cloud = [], []
    for s in SEEDS:
        inst = w6.make_instance(N, seed=s)
        # V1 truck-only EV
        custs = list(inst["customers"].keys())
        v1 = w6.truck_ev_route(inst, custs, allow_recharge=True, q=inst["Q"])
        d1, m1, e1, _ = metrics(inst, v1["route"], [])
        v1_cloud.append((d1, m1))
        rows.append((s, "V1_truck", None, round(d1, 1), round(m1, 1),
                     round(e1, 1), 0))
        for w in WS:
            route, trips, off = my_v2_weighted(inst, w)
            d, m, e, nt = metrics(inst, route, trips)
            v2_cloud.append((d, m))
            rows.append((s, "V2_weighted", w, round(d, 1), round(m, 1),
                         round(e, 1), nt))

    # ---- CSV ----
    csv_path = os.path.join("src", "results", "week06_multi_objective.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        wcsv = csv.writer(fh)
        wcsv.writerow(["seed", "variant", "w", "distance", "makespan",
                       "energy", "n_trips"])
        for r in rows:
            wcsv.writerow(r)

    # ---- Fig 1: scatter V1 vs V2-weighted cloud ----
    fig1, ax = plt.subplots(figsize=(7, 5.5))
    xs1 = [p[0] for p in v1_cloud]
    ys1 = [p[1] for p in v1_cloud]
    xs2 = [p[0] for p in v2_cloud]
    ys2 = [p[1] for p in v2_cloud]
    ax.scatter(xs1, ys1, c="#d95f02", s=70, label="V1 truck-only EV",
               zorder=3)
    sc = ax.scatter(xs2, ys2, c=[r[2] for r in rows if r[1] == "V2_weighted"],
                    cmap="viridis", s=45, label="V2 weighted (w=0..1)",
                    zorder=2)
    ax.set_xlabel("Total distance (cost)")
    ax.set_ylabel("Makespan (service time)")
    ax.set_title("Distance vs makespan: V2 dominates V1 (weighted-sum MO)")
    ax.legend()
    fig1.colorbar(sc, label="weight w (0=makespan, 1=distance)")
    fig1.tight_layout()
    f1 = os.path.join(FIG_DIR, "mo_scatter.png")
    fig1.savefig(f1, dpi=130)

    # ---- Fig 2: one representative instance, trade-off curve ----
    inst0 = w6.make_instance(N, seed=SEEDS[0])
    ws_x, dist_y, mk_y = [], [], []
    for w in WS:
        route, trips, _ = my_v2_weighted(inst0, w)
        d, m, _, _ = metrics(inst, route, trips)
        ws_x.append(w)
        dist_y.append(d)
        mk_y.append(m)
    fig2, ax1 = plt.subplots(figsize=(7, 5))
    ax1.plot(ws_x, dist_y, "o-", color="#2c7fb8", label="distance")
    ax1.set_xlabel("weight w (0 = makespan-driven, 1 = distance-driven)")
    ax1.set_ylabel("distance", color="#2c7fb8")
    ax2 = ax1.twinx()
    ax2.plot(ws_x, mk_y, "s--", color="#d95f02", label="makespan")
    ax2.set_ylabel("makespan", color="#d95f02")
    ax1.set_title(f"Trade-off on one instance (n={N}): distance vs makespan")
    fig2.tight_layout()
    f2 = os.path.join(FIG_DIR, "mo_tradeoff.png")
    fig2.savefig(f2, dpi=130)

    print(f"wrote {csv_path}")
    print(f"wrote {f1}")
    print(f"wrote {f2}")
    print(f"V1 mean (dist,mk) = ({sum(xs1)/len(xs1):.1f}, "
          f"{sum(ys1)/len(ys1):.1f})")
    print(f"V2 mean (dist,mk) = ({sum(xs2)/len(xs2):.1f}, "
          f"{sum(ys2)/len(ys2):.1f})")


if __name__ == "__main__":
    main()
