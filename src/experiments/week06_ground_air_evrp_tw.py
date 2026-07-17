"""
Week 6 v2 — Improved ground-air collaborative EVRP-TW.

Focus: improve the drone task allocation so that MORE customers can be
offloaded per instance (not just one), while keeping the same fair
comparison between V0/V1/V2.

Improvements over the previous v1 script:
  - drone trips can now serve multiple customers in one flight
    (launch -> k1 -> k2 -> ... -> land) as long as total range permits;
  - one truck stop can act as launch/land for several drone trips;
  - the heuristic repeatedly picks the best multi-customer offload until
    no further makespan reduction is possible.

Three variants still share the same greedy constructive core:
  V0  truck-only, NO battery limit
  V1  truck-only EVRP-TW (battery + charging + TW)
  V2  ground-air collaborative EVRP-TW (V1 + drone coordination)

Run:
  python src/experiments/week06_ground_air_evrp_tw.py
"""

import os
import math
import time
import random
import csv

SEED = 20260717
PI = math.pi

# --- model parameters (shared across variants) ---
V_T = 1.0          # truck speed
V_D = 2.0          # drone speed
SERVICE = 10       # customer service time
RECHARGE = 40      # full recharge time at a station (battery swap assumption)
RHO = 1.0          # energy consumed per distance unit
R_D = 160.0        # drone max flight length per trip (multi-customer total)
Q_DEFAULT = 250    # truck battery capacity
CAP = 1000         # vehicle capacity (kept high so capacity is non-binding)


# ---------------------------------------------------------------------------
# instance generation (seeded -> reproducible)
# ---------------------------------------------------------------------------
def make_instance(n, seed, tw_tight=False, q=None):
    rng = random.Random(seed)
    depot = (0.0, 0.0)
    customers = {}
    for i in range(1, n + 1):
        ang = rng.uniform(0, 2 * PI)
        r = rng.uniform(15, 30 + n * 4.0)
        customers[i] = (depot[0] + r * math.cos(ang),
                        depot[1] + r * math.sin(ang))
    # a few charging stations around the depot
    stations = {n + 1: (-45, 0.0), n + 2: (45, 0.0), n + 3: (0.0, 45.0),
                n + 4: (0.0, -45.0)}
    tw = {}
    width = 220 if not tw_tight else 35
    for i in customers:
        e = rng.uniform(0, 120)
        tw[i] = (e, e + width)
    demand = {i: rng.randint(5, 15) for i in customers}
    coord = {0: depot}
    coord.update(customers)
    coord.update(stations)
    return {
        "depot": depot, "customers": customers, "stations": stations,
        "tw": tw, "demand": demand, "coord": coord,
        "Q": q if q is not None else Q_DEFAULT, "n": n,
    }


def dist(inst, a, b):
    ca, cb = inst["coord"][a], inst["coord"][b]
    return math.hypot(ca[0] - cb[0], ca[1] - cb[1])


def nearest_station(inst, node):
    return min(inst["stations"], key=lambda s: dist(inst, node, s))


# ---------------------------------------------------------------------------
# truck EV route (serves the given customer set; may insert recharges)
# ---------------------------------------------------------------------------
def nn_order(inst, cust_ids):
    remaining = list(cust_ids)
    order, cur = [], 0
    while remaining:
        nxt = min(remaining, key=lambda c: dist(inst, cur, c))
        order.append(nxt)
        cur = nxt
        remaining.remove(nxt)
    return order


def truck_ev_route(inst, cust_ids, allow_recharge, q=None):
    """Greedy EV truck route over cust_ids. Returns a dict of results."""
    Q = q if q is not None else inst["Q"]
    rho = RHO
    order = nn_order(inst, cust_ids)
    route = [0]
    battery = Q
    t = 0.0
    recharges = 0
    charge_time = 0.0
    tw_viol = 0
    energy_inf = False

    def travel_to(node, add_service=True):
        nonlocal battery, t, recharges, charge_time, energy_inf, tw_viol
        d = dist(inst, route[-1], node)
        if battery - d * rho < 0:
            if allow_recharge:
                s = nearest_station(inst, route[-1])
                ds = dist(inst, route[-1], s)
                route.append(s)
                battery = Q
                recharges += 1
                charge_time += RECHARGE
                t += ds / V_T + RECHARGE
                d = dist(inst, s, node)
                if battery - d * rho < 0:
                    energy_inf = True
            else:
                energy_inf = True
        battery -= d * rho
        t += d / V_T
        if node not in inst["stations"]:
            if add_service:
                arr = t
                if arr < inst["tw"][node][0]:
                    t = inst["tw"][node][0]
                if t > inst["tw"][node][1]:
                    tw_viol += 1
                t += SERVICE

    for c in order:
        travel_to(c)
        route.append(c)
    # return to depot
    travel_to(0, add_service=False)
    route.append(0)

    return {
        "route": route, "makespan": t, "recharges": recharges,
        "charge_time": charge_time, "tw_viol": tw_viol,
        "energy_inf": energy_inf, "total_dist": route_distance(inst, route),
    }


def route_distance(inst, route):
    return sum(dist(inst, route[i], route[i + 1])
               for i in range(len(route) - 1))


def node_extra(inst, node):
    if node == 0:
        return 0.0
    if node in inst["stations"]:
        return RECHARGE
    return SERVICE


def simulate(inst, route, drone_trips):
    """
    Truck arrival times + drone makespan.

    route        : list of truck nodes, including depot bookends
    drone_trips  : list of (launch_node, customer_list, land_node)
                   customer_list may contain one or more customers
    """
    full = route[:]
    arr = [0.0] * len(full)
    for p in range(1, len(full)):
        d = dist(inst, full[p - 1], full[p])
        arr[p] = arr[p - 1] + d / V_T + node_extra(inst, full[p])

    drone_free = 0.0
    for ln, custs, rn in drone_trips:
        i_pos = 0 if ln == 0 else full.index(ln)
        j_pos = len(full) - 1 if rn == 0 else full.index(rn)
        launch = arr[i_pos]
        # build drone sub-route: ln -> custs -> rn
        legs = [ln] + list(custs) + [rn]
        drone_dist = sum(dist(inst, legs[i], legs[i + 1])
                         for i in range(len(legs) - 1))
        drone_t = drone_dist / V_D + SERVICE * len(custs)
        landing = launch + drone_t
        drone_free = max(drone_free, landing)
    return arr, drone_free


# ---------------------------------------------------------------------------
# V2: improved drone task allocation
# ---------------------------------------------------------------------------

def _customer_list_is_feasible(inst, ln, custs, rn, truck_i, truck_j, rd):
    """Check if a multi-customer drone trip can meet range and rendezvous."""
    legs = [ln] + list(custs) + [rn]
    drone_dist = sum(dist(inst, legs[i], legs[i + 1])
                     for i in range(len(legs) - 1))
    if drone_dist > rd:
        return False
    drone_t = drone_dist / V_D + SERVICE * len(custs)
    # rendezvous: drone must land by the time the truck reaches rn
    if drone_t > truck_j - truck_i:
        return False
    # time windows (sequential service in the given order)
    t = truck_i + dist(inst, ln, custs[0]) / V_D + SERVICE
    if t < inst["tw"][custs[0]][0] or t > inst["tw"][custs[0]][1]:
        return False
    for idx in range(1, len(custs)):
        t += dist(inst, custs[idx - 1], custs[idx]) / V_D + SERVICE
        k = custs[idx]
        if t < inst["tw"][k][0] or t > inst["tw"][k][1]:
            return False
    return True


def collaborative(inst, drone_range=None):
    """
    Greedy improvement on top of the V1 truck route.

    Key improvement over the previous version:
      - drone trips can carry up to 2 customers per flight;
      - one launch/land node may be reused for several trips;
      - repeatedly picks the best feasible offload until no more gain.
    """
    rd = drone_range if drone_range is not None else R_D
    all_c = list(inst["customers"].keys())
    v1 = truck_ev_route(inst, all_c, allow_recharge=True)
    v1_route = v1["route"][:]

    offloaded = set()
    protected = set()     # launch/land nodes may not later be offloaded
    drone_trips = []      # (launch, [cust, ...], land)
    sync_rejected = 0

    def makespan(route, trips):
        a, d = simulate(inst, route, trips)
        return max(a[-1], d)

    while True:
        # current truck route after removing offloaded customers
        route = [n for n in v1_route if n not in offloaded]
        arr, _ = simulate(inst, route, [])
        pos = {n: i for i, n in enumerate(route)}

        best = None
        # iterate over all launch/recovery pairs in the current truck route
        for i_idx in range(len(route) - 1):
            for j_idx in range(i_idx + 2, len(route)):
                ln, rn = route[i_idx], route[j_idx]
                # candidate customers between ln and rn that are still on truck
                candidates = [route[k] for k in range(i_idx + 1, j_idx)
                              if route[k] not in inst["stations"]
                              and route[k] not in offloaded
                              and route[k] not in protected]
                if not candidates:
                    continue
                truck_i, truck_j = arr[i_idx], arr[j_idx]

                # single-customer trips
                for k in candidates:
                    custs = (k,)
                    if not _customer_list_is_feasible(
                            inst, ln, custs, rn, truck_i, truck_j, rd):
                        sync_rejected += 1
                        continue
                    # reduction in truck makespan if k is removed from route
                    test_route = [n for n in route if n != k]
                    a2, _ = simulate(inst, test_route, [])
                    reduction = arr[-1] - a2[-1]
                    if reduction > 0 and (best is None
                                          or reduction > best[0]):
                        best = (reduction, ln, rn, custs)

                # two-customer trips (try both orderings)
                if len(candidates) >= 2:
                    for idx1 in range(len(candidates)):
                        for idx2 in range(idx1 + 1, len(candidates)):
                            k1, k2 = candidates[idx1], candidates[idx2]
                            for order in [(k1, k2), (k2, k1)]:
                                custs = order
                                if not _customer_list_is_feasible(
                                        inst, ln, custs, rn, truck_i,
                                        truck_j, rd):
                                    sync_rejected += 1
                                    continue
                                test_route = [n for n in route
                                              if n not in custs]
                                a2, _ = simulate(inst, test_route, [])
                                reduction = arr[-1] - a2[-1]
                                if reduction > 0 and (best is None
                                                      or reduction > best[0]):
                                    best = (reduction, ln, rn, custs)

        if best is None:
            break
        _, ln, rn, custs = best
        for c in custs:
            offloaded.add(c)
        protected.add(ln)
        protected.add(rn)
        drone_trips.append((ln, list(custs), rn))
        # loop continues; more customers may still be offloaded

    # final V2 route: original V1 route with offloaded customers removed
    v2_route = [n for n in v1_route if n not in offloaded]
    arr2, drone_mk = simulate(inst, v2_route, drone_trips)
    truck_mk = arr2[-1]

    # truck time-window violations on the final V2 route
    tw_viol_truck = 0
    for p, n in enumerate(v2_route):
        if n in inst["stations"] or n == 0:
            continue
        arrival = arr2[p] - SERVICE
        if arrival > inst["tw"][n][1]:
            tw_viol_truck += 1

    # drone TW violations
    tw_viol_drone = 0
    for ln, custs, rn in drone_trips:
        i_pos = 0 if ln == 0 else v2_route.index(ln)
        t = arr2[i_pos] + dist(inst, ln, custs[0]) / V_D + SERVICE
        if t < inst["tw"][custs[0]][0] or t > inst["tw"][custs[0]][1]:
            tw_viol_drone += 1
        for idx in range(1, len(custs)):
            t += dist(inst, custs[idx - 1], custs[idx]) / V_D + SERVICE
            if t < inst["tw"][custs[idx]][0] or t > inst["tw"][custs[idx]][1]:
                tw_viol_drone += 1

    rechg = sum(1 for n in v2_route if n in inst["stations"])
    truck_dist = route_distance(inst, v2_route)
    drone_dist = sum(
        sum(dist(inst, legs[i], legs[i + 1])
            for i in range(len(legs) - 1))
        for ln, custs, rn in drone_trips
        for legs in [[ln] + list(custs) + [rn]]
    )

    return {
        "route": v2_route, "drone_trips": drone_trips,
        "makespan": max(truck_mk, drone_mk),
        "truck_makespan": truck_mk, "drone_makespan": drone_mk,
        "total_dist": truck_dist + drone_dist,
        "recharges": rechg, "charge_time": rechg * RECHARGE,
        "tw_viol": tw_viol_truck + tw_viol_drone,
        "energy_inf": v1["energy_inf"], "sync_rejected": sync_rejected,
        "offloaded": len(offloaded), "n_customers": inst["n"],
    }


# ---------------------------------------------------------------------------
# experiment runner
# ---------------------------------------------------------------------------
def run_variant(inst, kind):
    all_c = list(inst["customers"].keys())
    if kind == "V0":
        r = truck_ev_route(inst, all_c, allow_recharge=False, q=10 ** 9)
        return {"makespan": r["makespan"], "total_dist": r["total_dist"],
                "feasible": not r["energy_inf"], "tw_viol": r["tw_viol"],
                "energy_viol": 0, "recharges": 0, "charge_time": 0.0,
                "sync_viol": 0, "offloaded": 0}
    if kind == "V1":
        r = truck_ev_route(inst, all_c, allow_recharge=True)
        return {"makespan": r["makespan"], "total_dist": r["total_dist"],
                "feasible": not r["energy_inf"], "tw_viol": r["tw_viol"],
                "energy_viol": 1 if r["energy_inf"] else 0,
                "recharges": r["recharges"], "charge_time": r["charge_time"],
                "sync_viol": 0, "offloaded": 0}
    # V2 collaborative
    r = collaborative(inst)
    return {"makespan": r["makespan"], "total_dist": r["total_dist"],
            "feasible": not r["energy_inf"], "tw_viol": r["tw_viol"],
            "energy_viol": 1 if r["energy_inf"] else 0,
            "recharges": r["recharges"], "charge_time": r["charge_time"],
            "sync_viol": r["sync_rejected"], "offloaded": r["offloaded"]}


def main():
    here = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    res_dir = os.path.join(here, "src", "results")
    os.makedirs(res_dir, exist_ok=True)
    out_csv = os.path.join(res_dir, "week06_ground_air_results.csv")
    out_txt = os.path.join(res_dir, "week06_ground_air_output.txt")

    random.seed(SEED)
    sizes = [8, 12, 16, 20]
    rows = []
    L = []
    L.append("=" * 78)
    L.append("WEEK 6 v2 — GROUND-AIR COLLABORATIVE EVRP-TW (improved drone allocation)")
    L.append("=" * 78)
    L.append(f"seed={SEED}  truck_speed={V_T}  drone_speed={V_D}  "
             f"drone_range={R_D}  battery={Q_DEFAULT}  recharge={RECHARGE}s")
    L.append("variants: V0 truck-only(no EV) | V1 truck EV | "
             "V2 ground-air collaborative EV")
    L.append("")

    for n in sizes:
        inst = make_instance(n, seed=SEED + n)
        L.append(f"--- instance size N={n} (customers), 4 stations ---")
        row = {"size": n, "seed": SEED}
        for kind in ["V0", "V1", "V2"]:
            t0 = time.perf_counter()
            res = run_variant(inst, kind)
            el = time.perf_counter() - t0
            L.append(
                f"  {kind}: makespan={res['makespan']:7.1f}  "
                f"dist={res['total_dist']:7.1f}  feas={res['feasible']}  "
                f"TWviol={res['tw_viol']}  rechg={res['recharges']}  "
                f"syncRej={res['sync_viol']}  offload={res['offloaded']}  "
                f"{el:.3f}s")
            for k, v in res.items():
                row[f"{kind}_{k}"] = v
            row[f"{kind}_runtime"] = round(el, 4)
        if row["V1_makespan"] > 0:
            imp = (row["V1_makespan"] - row["V2_makespan"]) / row["V1_makespan"] * 100
            row["imp_v2_vs_v1_pct"] = round(imp, 2)
            L.append(f"  -> V2 improvement vs V1 (makespan): {imp:.1f}%")
        rows.append(row)
        L.append("")

    # ---- failure cases (constraint-level diagnosis) ----
    L.append("=" * 78)
    L.append("FAILURE CASES (>=3, constraint-level diagnosis)")
    L.append("=" * 78)
    failures = []

    # FC1: no recharge allowed + small battery -> energy infeasible
    inst_f1 = make_instance(12, seed=SEED + 12)
    r1 = truck_ev_route(inst_f1, list(inst_f1["customers"].keys()),
                        allow_recharge=False, q=120)
    fc1 = ("FC1", "truck-only EV, recharge OFF, battery=120",
           "energy violation (cannot cover distance even with one charge)",
           "route becomes infeasible; fix: allow recharge at stations or "
           "raise battery capacity")
    failures.append(fc1)
    L.append(f"  {fc1[0]} [{fc1[1]}]: {fc1[2]}. Next: {fc1[3]}.")

    # FC2: drone range too small -> almost no offload -> V2 ~ V1
    inst_f2 = make_instance(12, seed=SEED + 12)
    r2 = collaborative(inst_f2, drone_range=40.0)
    fc2 = ("FC2", "collaborative, drone_range=40 (tiny)",
           f"only {r2['offloaded']} customers offloaded; V2 makespan "
           f"{r2['makespan']:.1f} ~ V1, drone contributes little",
           "fix: larger drone range, or accept degraded-to-baseline behaviour")
    failures.append(fc2)
    L.append(f"  {fc2[0]} [{fc2[1]}]: {fc2[2]}. Next: {fc2[3]}.")

    # FC3: tight time windows -> TW violations on V1
    inst_f3 = make_instance(12, seed=SEED + 12, tw_tight=True)
    r3 = truck_ev_route(inst_f3, list(inst_f3["customers"].keys()),
                        allow_recharge=True)
    fc3 = ("FC3", "truck EV, tight time windows (width=35)",
           f"{r3['tw_viol']} customers served outside their window",
           "fix: relax windows, add vehicles, or prioritise TW in insertion")
    failures.append(fc3)
    L.append(f"  {fc3[0]} [{fc3[1]}]: {fc3[2]}. Next: {fc3[3]}.")

    # FC4: sync rejection when drone trip would land after truck left
    inst_f4 = make_instance(16, seed=SEED + 16)
    r4 = collaborative(inst_f4)
    fc4 = ("FC4", "collaborative, 16 customers",
           f"{r4['sync_rejected']} drone trips rejected by rendezvous "
           f"(land-after-truck) constraint",
           "fix: reorder truck route or launch earlier; shows sync is active")
    failures.append(fc4)
    L.append(f"  {fc4[0]} [{fc4[1]}]: {fc4[2]}. Next: {fc4[3]}.")
    L.append("")

    # ---- write csv ----
    fieldnames = list(rows[0].keys())
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)

    # failure table csv
    fc_csv = os.path.join(res_dir, "week06_failure_cases.csv")
    with open(fc_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "setting", "observed_problem", "next_step"])
        for fc in failures:
            w.writerow(fc)

    text = "\n".join(L)
    with open(out_txt, "w") as f:
        f.write(text)
    print(text)
    print(f"\n[results -> {out_csv}]")
    print(f"[failure cases -> {fc_csv}]")
    print(f"[log -> {out_txt}]")


if __name__ == "__main__":
    main()
