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

The completion-time evaluator enforces a physically executable single-drone
schedule: the truck waits at a recovery node for its drone, and a sortie may
only launch after the previous one has been recovered.

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


def route_positions(route):
    """First and last position of every node along the truck route.

    The depot sits at both bookends, so a launch node resolves to its first
    occurrence and a recovery node to its last one.
    """
    first, last = {}, {}
    for idx, node in enumerate(route):
        first.setdefault(node, idx)
        last[node] = idx
    return first, last


def _accepted_sortie_intervals(route, drone_trips):
    """Truck-route intervals already claimed by accepted sorties.

    A single drone is a serial resource, so a new sortie may not overlap any of
    these; sharing an endpoint is fine (the drone is back on the truck there).
    """
    first, last = route_positions(route)
    out = []
    for ln, _custs, rn in drone_trips:
        if ln in first and rn in last:
            out.append((first[ln], last[rn]))
    return out


def _overlaps(i_pos, j_pos, intervals):
    return any(not (j_pos <= a or i_pos >= b) for a, b in intervals)


def simulate(inst, route, drone_trips, rd=None):
    """
    Truck arrival times + drone mission finish time for a single-drone plan.

    route        : list of truck nodes, including depot bookends
    drone_trips  : list of (launch_node, customer_list, land_node)
                   customer_list may contain one or more customers

    This is the same physical model as the shared FSTSP evaluator
    (week07_fstsp_repro.fstsp_simulate): the truck waits at a recovery node
    until the drone has landed there, and one drone is one serial resource, so
    a sortie can only launch once the previous one has been recovered. A plan
    is infeasible (drone finish time math.inf) when a launch does not precede
    its recovery, when a flight is longer than the range rd, when a sortie
    would start while the drone is still in the air, or when the launch or
    recovery node is not on the route.
    """
    rd = R_D if rd is None else rd
    full = route[:]
    arr = [0.0] * len(full)
    for p in range(1, len(full)):
        d = dist(inst, full[p - 1], full[p])
        arr[p] = arr[p - 1] + d / V_T + node_extra(inst, full[p])

    if not drone_trips:
        return arr, 0.0

    first, last = route_positions(full)
    trips = sorted(drone_trips, key=lambda t: first.get(t[0], len(full)))
    drone_free = 0.0
    for ln, custs, rn in trips:
        if ln not in first or rn not in last:
            return arr, math.inf
        i_pos, j_pos = first[ln], last[rn]
        if i_pos >= j_pos:
            return arr, math.inf
        # build drone sub-route: ln -> custs -> rn
        legs = [ln] + list(custs) + [rn]
        drone_dist = sum(dist(inst, legs[i], legs[i + 1])
                         for i in range(len(legs) - 1))
        if drone_dist > rd + 1e-9:
            return arr, math.inf
        # the drone has to be back on the truck when it reaches the launch node
        if drone_free > arr[i_pos] + 1e-9:
            return arr, math.inf
        flight = drone_dist / V_D + SERVICE * len(custs)
        landing = arr[i_pos] + flight
        truck_at_rec = arr[j_pos]
        recovery = max(truck_at_rec, landing)
        drone_free = recovery
        wait = recovery - truck_at_rec
        if wait > 0:
            for p in range(j_pos, len(arr)):
                arr[p] += wait
    return arr, drone_free


# ---------------------------------------------------------------------------
# V2: improved drone task allocation
# ---------------------------------------------------------------------------

def _customer_list_is_feasible(inst, ln, custs, rn, launch_time, rd):
    """Cheap pre-filter before the evaluator: range and the drone's own
    time windows (sequential service in the given order). Physical scheduling
    feasibility itself is decided by `simulate`.
    """
    legs = [ln] + list(custs) + [rn]
    drone_dist = sum(dist(inst, legs[i], legs[i + 1])
                     for i in range(len(legs) - 1))
    if drone_dist > rd:
        return False
    t = launch_time + dist(inst, ln, custs[0]) / V_D + SERVICE
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

    while True:
        # current truck route after removing offloaded customers
        route = [n for n in v1_route if n not in offloaded]
        arr_cur, drone_cur = simulate(inst, route, drone_trips, rd)
        if math.isinf(drone_cur):
            break
        mk_current = max(arr_cur[-1], drone_cur)
        accepted = _accepted_sortie_intervals(route, drone_trips)

        best = None
        # iterate over all launch/recovery pairs in the current truck route
        for i_idx in range(len(route) - 1):
            for j_idx in range(i_idx + 2, len(route)):
                ln, rn = route[i_idx], route[j_idx]
                # one drone is one serial resource: a new sortie may not
                # overlap an accepted one
                if _overlaps(i_idx, j_idx, accepted):
                    sync_rejected += 1
                    continue
                # candidate customers between ln and rn that are still on truck
                candidates = [route[k] for k in range(i_idx + 1, j_idx)
                              if route[k] not in inst["stations"]
                              and route[k] not in offloaded
                              and route[k] not in protected]
                if not candidates:
                    continue

                def consider(custs, ln=ln, rn=rn):
                    """Keep this sortie only if the physical plan improves."""
                    nonlocal best, sync_rejected
                    test_route = [n for n in route if n not in custs]
                    new_trips = drone_trips + [(ln, list(custs), rn)]
                    a2, d2 = simulate(inst, test_route, new_trips, rd)
                    if math.isinf(d2):
                        sync_rejected += 1
                        return
                    gain = mk_current - max(a2[-1], d2)
                    if gain > 0 and (best is None or gain > best[0]):
                        best = (gain, ln, rn, custs)

                # single-customer trips
                for k in candidates:
                    custs = (k,)
                    if not _customer_list_is_feasible(
                            inst, ln, custs, rn, arr_cur[i_idx], rd):
                        sync_rejected += 1
                        continue
                    consider(custs)

                # two-customer trips (try both orderings)
                if len(candidates) >= 2:
                    for idx1 in range(len(candidates)):
                        for idx2 in range(idx1 + 1, len(candidates)):
                            k1, k2 = candidates[idx1], candidates[idx2]
                            for custs in [(k1, k2), (k2, k1)]:
                                if not _customer_list_is_feasible(
                                        inst, ln, custs, rn,
                                        arr_cur[i_idx], rd):
                                    sync_rejected += 1
                                    continue
                                consider(custs)

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
    arr2, drone_mk = simulate(inst, v2_route, drone_trips, rd)
    plan_valid = not math.isinf(drone_mk)
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
        "makespan": max(truck_mk, drone_mk) if plan_valid
        else float("inf"),
        "truck_makespan": truck_mk, "drone_makespan": drone_mk,
        "total_dist": truck_dist + drone_dist,
        "recharges": rechg, "charge_time": rechg * RECHARGE,
        "tw_viol": tw_viol_truck + tw_viol_drone,
        "energy_inf": v1["energy_inf"], "sync_rejected": sync_rejected,
        "plan_valid": plan_valid,
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
                "sync_viol": 0, "offloaded": 0, "plan_valid": True}
    if kind == "V1":
        r = truck_ev_route(inst, all_c, allow_recharge=True)
        return {"makespan": r["makespan"], "total_dist": r["total_dist"],
                "feasible": not r["energy_inf"], "tw_viol": r["tw_viol"],
                "energy_viol": 1 if r["energy_inf"] else 0,
                "recharges": r["recharges"], "charge_time": r["charge_time"],
                "sync_viol": 0, "offloaded": 0, "plan_valid": True}
    # V2 collaborative
    r = collaborative(inst)
    return {"makespan": r["makespan"], "total_dist": r["total_dist"],
            "feasible": (not r["energy_inf"]) and r["plan_valid"],
            "tw_viol": r["tw_viol"],
            "energy_viol": 1 if r["energy_inf"] else 0,
            "recharges": r["recharges"], "charge_time": r["charge_time"],
            "sync_viol": r["sync_rejected"], "offloaded": r["offloaded"],
            "plan_valid": r["plan_valid"]}


def _mean(vals):
    return sum(vals) / len(vals) if vals else 0.0


def _rate(vals):
    return sum(1 for v in vals if v) / len(vals) if vals else 0.0


def main():
    here = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    res_dir = os.path.join(here, "src", "results")
    os.makedirs(res_dir, exist_ok=True)
    out_raw = os.path.join(res_dir, "week06_ground_air_results.csv")
    out_summary = os.path.join(res_dir, "week06_ground_air_summary.csv")
    out_txt = os.path.join(res_dir, "week06_ground_air_output.txt")

    N_SEEDS = 10
    SIZES = [8, 12, 16, 20]
    SEED_BASE = 20260720

    L = []
    L.append("=" * 78)
    L.append("WEEK 6 v2 — GROUND-AIR COLLABORATIVE EVRP-TW (multi-seed experiment)")
    L.append("=" * 78)
    L.append(f"seeds={N_SEEDS} (base {SEED_BASE}..{SEED_BASE + N_SEEDS - 1})  "
             f"sizes={SIZES}")
    L.append(f"truck_speed={V_T}  drone_speed={V_D}  drone_range={R_D}  "
             f"battery={Q_DEFAULT}  recharge={RECHARGE}s")
    L.append("variants: V0 truck-only(no EV) | V1 truck EV | "
             "V2 ground-air collaborative EV")
    L.append(f"total instances = {N_SEEDS * len(SIZES)} "
             f"(>=10 instances, 4 scales, multiple seeds)")
    L.append("")

    raw_rows = []
    # per-size accumulation of variant result dicts
    acc = {n: {"V0": [], "V1": [], "V2": []} for n in SIZES}

    for n in SIZES:
        L.append(f"=== size N={n} ===")
        for s in range(N_SEEDS):
            seed = SEED_BASE + s
            inst = make_instance(n, seed=seed)
            row = {"size": n, "seed": seed}
            vd = {}
            for kind in ["V0", "V1", "V2"]:
                t0 = time.perf_counter()
                res = run_variant(inst, kind)
                el = time.perf_counter() - t0
                res["runtime"] = round(el, 4)
                vd[kind] = res
                for k, v in res.items():
                    row[f"{kind}_{k}"] = v
            if row["V1_makespan"] > 0:
                imp = (row["V1_makespan"] - row["V2_makespan"]) / \
                    row["V1_makespan"] * 100
                row["imp_v2_vs_v1_pct"] = round(imp, 2)
                L.append(
                    f"  seed {seed}: V0={vd['V0']['makespan']:7.1f} "
                    f"V1={vd['V1']['makespan']:7.1f} "
                    f"V2={vd['V2']['makespan']:7.1f}  "
                    f"imp={imp:5.1f}%  off={vd['V2']['offloaded']}/{n}  "
                    f"feas(V0/V1/V2)="
                    f"{int(vd['V0']['feasible'])}/"
                    f"{int(vd['V1']['feasible'])}/"
                    f"{int(vd['V2']['feasible'])}")
            else:
                row["imp_v2_vs_v1_pct"] = 0.0
            raw_rows.append(row)
            acc[n]["V0"].append(vd["V0"])
            acc[n]["V1"].append(vd["V1"])
            acc[n]["V2"].append(vd["V2"])
        L.append("")

    # ---- aggregation ----
    L.append("=" * 78)
    L.append("AGGREGATE (mean over seeds per size)")
    L.append("=" * 78)
    summary_rows = []
    hdr = ("size | n_inst | V0_mk | V1_mk | V2_mk | imp% | "
           "offload | offload% | V0_feas | V1_feas | V2_feas | "
           "V2_plan_ok | "
           "syncRej | rechg | TWviol | runtime")
    L.append("  " + hdr)
    for n in SIZES:
        v0, v1, v2 = acc[n]["V0"], acc[n]["V1"], acc[n]["V2"]
        imp = _mean([(r1["makespan"] - r2["makespan"]) / r1["makespan"] * 100
                     for r1, r2 in zip(v1, v2) if r1["makespan"] > 0])
        off_rate = _mean([r["offloaded"] / n * 100 for r in v2])
        srow = {
            "size": n,
            "n_instances": N_SEEDS,
            "V0_makespan": round(_mean([r["makespan"] for r in v0]), 1),
            "V1_makespan": round(_mean([r["makespan"] for r in v1]), 1),
            "V2_makespan": round(_mean([r["makespan"] for r in v2]), 1),
            "imp_v2_vs_v1_pct": round(imp, 1),
            "V2_offloaded": round(_mean([r["offloaded"] for r in v2]), 1),
            "V2_offload_rate_pct": round(off_rate, 1),
            "V0_feas_rate": round(_rate([r["feasible"] for r in v0]), 3),
            "V1_feas_rate": round(_rate([r["feasible"] for r in v1]), 3),
            "V2_feas_rate": round(_rate([r["feasible"] for r in v2]), 3),
            "V2_plan_valid_rate": round(
                _rate([r["plan_valid"] for r in v2]), 3),
            "V2_sync_rej_mean": round(_mean([r["sync_viol"] for r in v2]), 1),
            "V2_recharges_mean": round(_mean([r["recharges"] for r in v2]), 1),
            "V2_tw_viol_mean": round(_mean([r["tw_viol"] for r in v2]), 1),
            "V2_runtime_mean": round(_mean([r["runtime"] for r in v2]), 4),
        }
        summary_rows.append(srow)
        L.append(
            f"  N={n}: V0={srow['V0_makespan']:7.1f} "
            f"V1={srow['V1_makespan']:7.1f} V2={srow['V2_makespan']:7.1f}  "
            f"imp={srow['imp_v2_vs_v1_pct']:5.1f}%  "
            f"offload={srow['V2_offloaded']:.1f}/{n} "
            f"({srow['V2_offload_rate_pct']:.1f}%)  "
            f"V2_feas={srow['V2_feas_rate'] * 100:.0f}%")
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

    # FC4: sorties refused by the physical single-drone schedule
    inst_f4 = make_instance(16, seed=SEED + 16)
    r4 = collaborative(inst_f4)
    fc4 = ("FC4", "collaborative, 16 customers",
           f"{r4['sync_rejected']} drone trips refused by the single-drone "
           f"schedule (range, launch order, or a drone still in flight)",
           "fix: reorder truck route or launch earlier; shows sync is active")
    failures.append(fc4)
    L.append(f"  {fc4[0]} [{fc4[1]}]: {fc4[2]}. Next: {fc4[3]}.")
    L.append("")

    # ---- write csv ----
    fieldnames = list(raw_rows[0].keys())
    with open(out_raw, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in raw_rows:
            w.writerow(row)

    sfields = list(summary_rows[0].keys())
    with open(out_summary, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sfields)
        w.writeheader()
        for row in summary_rows:
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
    print(f"\n[raw results -> {out_raw}]")
    print(f"[summary (avg) -> {out_summary}]")
    print(f"[failure cases -> {fc_csv}]")
    print(f"[log -> {out_txt}]")


if __name__ == "__main__":
    main()
