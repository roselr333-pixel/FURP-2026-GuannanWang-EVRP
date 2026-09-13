"""
Week 7 — Reproduce a published method (Murray & Chu 2015, FSTSP) and put it
on the SAME stage as "my heuristic".

Goal (per the user's request): reproduce the flying-sidekick TSP (FSTSP)
heuristic from Murray, C. C., & Chu, A. G. (2015), Transportation Research
Part C, 54, 86-109, and compare it head-to-head with my own ground-air
collaborative heuristic on IDENTICAL instances and with ONE shared evaluator.

What is faithful to the paper (Section 3.3, Algorithms 1-4):
  - One truck + ONE drone; the drone is carried by the truck, launched from a
    truck node, serves customer(s), and is recovered by the truck at a later
    node on the truck route (the "rendezvous" / synchronization constraint).
  - Because there is only one drone, sorties are SERIAL: a new sortie can only
    launch after the previous one has been recovered (the drone is back on the
    truck). The shared evaluator below enforces this strictly, including the
    rendezvous geometry: a sortie may only launch from a truck node the truck has
    not yet passed. A sortie set that violates this (e.g. one sortie nested
    inside another) is not physically realisable and is reported as infeasible
    (inf) rather than being given a makespan.
  - The heuristic is a "route and re-assign" greedy: start with a TSP tour
    that assigns the truck to every customer, then repeatedly move a customer
    from the truck to the drone if it reduces the completion time.
  - Feasibility: a drone sortie's length must not exceed its endurance (range).

Simplification I make (documented, not hidden): the paper also has a
calcCostTruck step that can re-insert a customer into the truck route or move
it between sub-routes. I implement the core truck->UAV insertion (the main
contribution) and skip the secondary re-insertions. The objective I report is
the exact FSTSP completion time computed by the sequential evaluator.

"My heuristic" here = my V2 greedy (from week06) but run in FSTSP mode:
no battery, no time windows, rendezvous via truck-wait, and it additionally
allows a single flight to serve up to TWO customers and one stop to be reused
for several launches. The shared evaluator makes the comparison apples-to-apples.

Run:
  python src/experiments/week07_fstsp_repro.py
"""

import os
import sys
import time
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import week06_ground_air_evrp_tw as w6   # reuse geometry + instance generator

V_T = w6.V_T          # truck speed
V_D = w6.V_D          # drone speed
SERVICE = w6.SERVICE  # customer service time
R_D = w6.R_D          # drone max flight length per sortie (range)
INF = float("inf")


# ---------------------------------------------------------------------------
# FSTSP evaluator (Murray & Chu completion time) with ONE serial drone
# ---------------------------------------------------------------------------
def _tt(inst, a, b):
    """Truck travel time between two nodes (no service)."""
    return w6.dist(inst, a, b) / V_T


def _service(node):
    return SERVICE if node != 0 else 0.0


def _resolve(route, node, role):
    """Position of `node` in `route`. The depot (0) appears at both ends, so
    a launch uses the first occurrence and a recovery uses the last."""
    if node == 0:
        return 0 if role == "launch" else len(route) - 1
    return route.index(node)


def fstsp_simulate(inst, route, drone_trips):
    """
    Truck arrival (+service) times along `route` (depot bookends), with the
    truck waiting at a recovery node if the drone has not yet landed, AND with
    a single serial drone.

    Physical validity: a sortie launches at a truck node i and is recovered at a
    later node j (i before j on the route), its flight length is within range,
    and the drone must be back on the truck before the truck reaches i --
    otherwise the sortie would have to launch from a node the truck has already
    left, which no feasible plan realises. If any of these is violated the plan
    is infeasible and the function returns an all-inf array.

    route        : [0, ...truck nodes..., 0]
    drone_trips  : (launch_node, cust_or_custs, recover_node)
    Returns the arrival-time array (len == len(route)), or [inf] * len(route).
    """
    arr = [0.0] * len(route)
    for p in range(1, len(route)):
        arr[p] = arr[p - 1] + _tt(inst, route[p - 1], route[p]) \
            + _service(route[p])

    if not drone_trips:
        return arr

    # process sorties in launch order; the drone is a single serial resource
    trips = sorted(drone_trips,
                   key=lambda t: _resolve(route, t[0], "launch"))
    drone_free = 0.0
    for ln, cust, rn in trips:
        i_pos = _resolve(route, ln, "launch")
        j_pos = _resolve(route, rn, "recover")
        if i_pos >= j_pos:
            return [INF] * len(route)
        cl = list(cust) if isinstance(cust, (list, tuple)) else [cust]
        legs = [ln] + cl + [rn]
        d = sum(w6.dist(inst, legs[p], legs[p + 1])
                for p in range(len(legs) - 1))
        if d > R_D + 1e-9:
            return [INF] * len(route)
        # the drone must be back on the truck before the truck reaches i
        if drone_free > arr[i_pos] + 1e-9:
            return [INF] * len(route)
        flight = d / V_D + SERVICE * len(cl)
        landing = arr[i_pos] + flight
        truck_at_rec = arr[j_pos]
        recovery = max(truck_at_rec, landing)
        drone_free = recovery
        wait = recovery - truck_at_rec
        if wait > 0:
            for p in range(j_pos, len(arr)):
                arr[p] += wait
    return arr


def fstsp_makespan(inst, route, drone_trips):
    """FSTSP completion time = time the truck returns to depot with the drone."""
    return fstsp_simulate(inst, route, drone_trips)[-1]


def fstsp_simulate_multi(inst, route, drone_trips, n_drones):
    """Same model as fstsp_simulate but with `n_drones` parallel serial drones
    carried by the truck (a multi-drone extension).

    Each sortie is served by whichever drone can start earliest; a drone is a
    serial resource whose next sortie starts only after its previous one has
    been recovered. The truck still waits at a recovery node until the sortie
    landing there has arrived. n_drones=1 reproduces fstsp_simulate exactly.

    Physical validity is enforced as in `fstsp_simulate`: launch before recover,
    flight within range, and at least one drone back on the truck when the truck
    reaches the launch node. An infeasible sortie set yields an all-inf array."""
    arr = [0.0] * len(route)
    for p in range(1, len(route)):
        arr[p] = arr[p - 1] + _tt(inst, route[p - 1], route[p]) \
            + _service(route[p])
    if not drone_trips:
        return arr
    trips = sorted(drone_trips,
                   key=lambda t: _resolve(route, t[0], "launch"))
    avail = [0.0] * n_drones
    for ln, cust, rn in trips:
        i_pos = _resolve(route, ln, "launch")
        j_pos = _resolve(route, rn, "recover")
        if i_pos >= j_pos:
            return [INF] * len(route)
        cl = list(cust) if isinstance(cust, (list, tuple)) else [cust]
        legs = [ln] + cl + [rn]
        d = sum(w6.dist(inst, legs[p], legs[p + 1])
                for p in range(len(legs) - 1))
        if d > R_D + 1e-9:
            return [INF] * len(route)
        flight = d / V_D + SERVICE * len(cl)
        starts = [max(arr[i_pos], avail[k]) for k in range(n_drones)]
        k = min(range(n_drones), key=lambda z: (starts[z], z))
        # at least one drone must be back on the truck when it reaches i
        if starts[k] > arr[i_pos] + 1e-9:
            return [INF] * len(route)
        landing = arr[i_pos] + flight
        truck_at_rec = arr[j_pos]
        recovery = max(truck_at_rec, landing)
        avail[k] = recovery
        wait = recovery - truck_at_rec
        if wait > 0:
            for p in range(j_pos, len(arr)):
                arr[p] += wait
    return arr


def fstsp_makespan_multi(inst, route, drone_trips, n_drones):
    """Completion time with `n_drones` parallel serial drones."""
    return fstsp_simulate_multi(inst, route, drone_trips, n_drones)[-1]


def _truck_travel(inst, route, a_pos, b_pos):
    """Truck travel time from route[a_pos] to route[b_pos] (incl. service at
    intermediate nodes and at b)."""
    t = 0.0
    for p in range(a_pos, b_pos):
        t += _tt(inst, route[p], route[p + 1])
    for p in range(a_pos + 1, b_pos + 1):
        t += _service(route[p])
    return t


def _remove_saving(inst, route, c):
    """Truck time saved by removing customer c from the truck route
    (edge-exchange saving: pred->c->succ replaced by pred->succ)."""
    cp = route.index(c)
    pred = route[cp - 1]
    succ = route[cp + 1]
    s = (_tt(inst, pred, c) + SERVICE) + (_tt(inst, c, succ) + SERVICE) \
        - (_tt(inst, pred, succ) + (SERVICE if succ != 0 else 0.0))
    return s


# ---------------------------------------------------------------------------
# Published method: Murray & Chu (2015) FSTSP insertion heuristic
#   - single customer per drone sortie (canonical version)
#   - a move is accepted only if the EXACT sequential evaluator confirms a
#     strict makespan reduction (the local savings/cost from Algorithms 2 & 4
#     is used as a cheap pre-filter)
# ---------------------------------------------------------------------------
def fstsp_insertion(inst, drone_range=None):
    rd = drone_range if drone_range is not None else R_D
    all_c = list(inst["customers"].keys())
    route = [0] + w6.nn_order(inst, all_c) + [0]
    drone_trips = []          # (launch, cust, recover)
    offloaded = set()
    protected = set()         # launch/recovery nodes may not later be offloaded

    while True:
        base = fstsp_makespan(inst, route, drone_trips)
        best = None           # (true_net, j, a, b, ap, bp)
        for jpos in range(1, len(route) - 1):
            j = route[jpos]
            if j == 0 or j in offloaded or j in protected:
                continue
            i = route[jpos - 1]
            k = route[jpos + 1]
            t_ij = _tt(inst, i, j) + SERVICE
            t_jk = _tt(inst, j, k) + SERVICE
            t_ik = _tt(inst, i, k) + (SERVICE if k != 0 else 0.0)
            savings = t_ij + t_jk - t_ik
            for ap in range(0, jpos):
                a = route[ap]
                for bp in range(jpos + 1, len(route)):
                    b = route[bp]
                    d = w6.dist(inst, a, j) + w6.dist(inst, j, b)
                    if d > rd:
                        continue
                    flight = d / V_D + SERVICE
                    tt_ab = _truck_travel(inst, route, ap, bp)
                    delay = max(0.0, flight - (tt_ab - savings))
                    if savings - delay <= 0:
                        continue
                    # verify with the exact sequential evaluator
                    new_route = [n for n in route if n != j]
                    new_trips = drone_trips + [(a, j, b)]
                    true_net = base - fstsp_makespan(inst, new_route,
                                                    new_trips)
                    if true_net > 0 and (best is None
                                         or true_net > best[0]):
                        best = (true_net, j, a, b, ap, bp)
        if best is None:
            break
        _, j, a, b, ap, bp = best
        offloaded.add(j)
        protected.add(a)
        protected.add(b)
        drone_trips.append((a, j, b))
        route = [n for n in route if n != j]
    return route, drone_trips, offloaded


# ---------------------------------------------------------------------------
# My heuristic in FSTSP mode: same greedy, but a flight may serve up to TWO
# customers and one stop may launch several sorties (my V2 extension).
# Selection is still validated by the exact sequential evaluator.
# ---------------------------------------------------------------------------
def my_v2_fstsp(inst, drone_range=None):
    rd = drone_range if drone_range is not None else R_D
    all_c = list(inst["customers"].keys())
    route = [0] + w6.nn_order(inst, all_c) + [0]
    drone_trips = []          # (launch, custs_tuple, recover)
    offloaded = set()
    protected = set()

    while True:
        base = fstsp_makespan(inst, route, drone_trips)
        best = None           # (true_net, ln, rn, custs)
        n = len(route)
        for i_idx in range(n - 1):
            ln = route[i_idx]
            for j_idx in range(i_idx + 2, n):
                rn = route[j_idx]
                cands = [route[p] for p in range(i_idx + 1, j_idx)
                         if route[p] != 0 and route[p] not in offloaded
                         and route[p] not in protected]
                if not cands:
                    continue
                tt_lr = _truck_travel(inst, route, i_idx, j_idx)
                # single-customer sorties
                for c in cands:
                    d = w6.dist(inst, ln, c) + w6.dist(inst, c, rn)
                    if d > rd:
                        continue
                    s = _remove_saving(inst, route, c)
                    flight = d / V_D + SERVICE
                    delay = max(0.0, flight - (tt_lr - s))
                    if s - delay <= 0:
                        continue
                    custs = (c,)
                    new_route = [x for x in route if x not in custs]
                    new_trips = drone_trips + [(ln, custs, rn)]
                    true_net = base - fstsp_makespan(inst, new_route,
                                                    new_trips)
                    if true_net > 0 and (best is None
                                         or true_net > best[0]):
                        best = (true_net, ln, rn, custs)
                # two-customer sorties (both orderings)
                if len(cands) >= 2:
                    for x in range(len(cands)):
                        for y in range(x + 1, len(cands)):
                            for order in [(cands[x], cands[y]),
                                         (cands[y], cands[x])]:
                                c1, c2 = order
                                d = (w6.dist(inst, ln, c1)
                                     + w6.dist(inst, c1, c2)
                                     + w6.dist(inst, c2, rn))
                                if d > rd:
                                    continue
                                s = (_remove_saving(inst, route, c1)
                                     + _remove_saving(inst, route, c2))
                                flight = d / V_D + 2 * SERVICE
                                delay = max(0.0, flight - (tt_lr - s))
                                if s - delay <= 0:
                                    continue
                                custs = order
                                new_route = [x for x in route
                                             if x not in custs]
                                new_trips = drone_trips + [(ln, custs, rn)]
                                true_net = base - fstsp_makespan(
                                    inst, new_route, new_trips)
                                if true_net > 0 and (best is None
                                                     or true_net > best[0]):
                                    best = (true_net, ln, rn, custs)
        if best is None:
            break
        _, ln, rn, custs = best
        for c in custs:
            offloaded.add(c)
        protected.add(ln)
        protected.add(rn)
        drone_trips.append((ln, custs, rn))
        route = [x for x in route if x not in custs]
    return route, drone_trips, offloaded


# ---------------------------------------------------------------------------
# 2-opt local search post-processor for the truck route
# (per progress_report §3.3-②: quantify the cost of "greedy without LS")
# Accept move iff makespan strictly improves (or stays equal and feasibility OK)
# ---------------------------------------------------------------------------
def my_v2_fstsp_with_2opt(inst, drone_range=None, max_passes=10):
    """Run my_v2_fstsp, then apply 2-opt on the truck route (intra-route, with
    fixed drone trips).  Accept a move only if the EXACT sequential evaluator
    says the makespan strictly improves."""
    route, trips, off = my_v2_fstsp(inst, drone_range=drone_range)
    base = fstsp_makespan(inst, route, trips)
    if base == float("inf"):
        return route, trips, off, base, 0
    improves = 0
    for _ in range(max_passes):
        moved = False
        # route[1:-1] are truck customer positions (depot bookends)
        seq = route[1:-1]
        m = len(seq)
        for a in range(m - 1):
            for b in range(a + 1, m):
                rev = seq[:a] + seq[a:b + 1][::-1] + seq[b + 1:]
                cand = [0] + rev + [0]
                new_mk = fstsp_makespan(inst, cand, trips)
                if new_mk < base - 1e-9:
                    route, base, seq = cand, new_mk, rev
                    improves += 1
                    moved = True
        if not moved:
            break
    return route, trips, off, base, improves


# ---------------------------------------------------------------------------
# experiment runner: same instances as week06, multiple seeds
# ---------------------------------------------------------------------------
def _mean(vals):
    return sum(vals) / len(vals) if vals else 0.0


def main():
    here = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    res_dir = os.path.join(here, "src", "results")
    os.makedirs(res_dir, exist_ok=True)
    out_raw = os.path.join(res_dir, "week07_fstsp_raw.csv")
    out_summary = os.path.join(res_dir, "week07_fstsp_summary.csv")
    out_txt = os.path.join(res_dir, "week07_fstsp_log.txt")

    N_SEEDS = 10
    SIZES = [8, 12, 16, 20]
    SEED_BASE = 20260720     # identical seeds as the week06 multi-seed run

    L = []
    L.append("=" * 78)
    L.append("WEEK 7 — FSTSP reproduction (Murray & Chu 2015) vs my heuristic")
    L.append("=" * 78)
    L.append(f"seeds={N_SEEDS} (base {SEED_BASE}..{SEED_BASE + N_SEEDS - 1})  "
             f"sizes={SIZES}")
    L.append(f"truck_speed={V_T}  drone_speed={V_D}  drone_range={R_D}  "
             f"service={SERVICE}")
    L.append("shared evaluator: FSTSP completion time with ONE serial drone")
    L.append("  (truck returns to depot, waiting for the drone at recovery;")
    L.append("   drone sorties are sequential). No battery, no TW.")
    L.append(f"total instances = {N_SEEDS * len(SIZES)}")
    L.append("")

    raw_rows = []
    acc = {n: {"truck": [], "pub": [], "my": [], "my_ls": [],
               "ls_improves": []} for n in SIZES}

    for n in SIZES:
        L.append(f"=== size N={n} ===")
        for s in range(N_SEEDS):
            seed = SEED_BASE + s
            inst = w6.make_instance(n, seed=seed)

            r0 = fstsp_makespan(inst, [0] + w6.nn_order(inst,
                                list(inst["customers"].keys())) + [0], [])
            t0 = time.perf_counter()
            pub_route, pub_trips, pub_off = fstsp_insertion(inst)
            rt_pub = time.perf_counter() - t0
            mk_pub = fstsp_makespan(inst, pub_route, pub_trips)

            t0 = time.perf_counter()
            my_route, my_trips, my_off = my_v2_fstsp(inst)
            rt_my = time.perf_counter() - t0
            mk_my = fstsp_makespan(inst, my_route, my_trips)

            # --- 2-opt post-processor on top of V2 (§3.3-②) ---
            t0 = time.perf_counter()
            _my2_route, _my2_trips, my2_off, mk_my_ls, n_ls_improves = \
                my_v2_fstsp_with_2opt(inst)
            rt_my_ls = time.perf_counter() - t0

            imp_pub = (r0 - mk_pub) / r0 * 100 if r0 > 0 else 0.0
            imp_my = (r0 - mk_my) / r0 * 100 if r0 > 0 else 0.0
            imp_my_vs_pub = (mk_pub - mk_my) / mk_pub * 100 if mk_pub > 0 else 0.0
            imp_my_ls_vs_my = (mk_my - mk_my_ls) / mk_my * 100 \
                if mk_my > 0 else 0.0
            imp_my_ls_vs_pub = (mk_pub - mk_my_ls) / mk_pub * 100 \
                if mk_pub > 0 else 0.0

            raw_rows.append({
                "size": n, "seed": seed,
                "truck_only_mk": round(r0, 1),
                "published_mk": round(mk_pub, 1),
                "my_mk": round(mk_my, 1),
                "my_ls_mk": round(mk_my_ls, 1),
                "imp_pub_pct": round(imp_pub, 1),
                "imp_my_pct": round(imp_my, 1),
                "imp_my_vs_pub_pct": round(imp_my_vs_pub, 1),
                "imp_my_ls_vs_my_pct": round(imp_my_ls_vs_my, 2),
                "imp_my_ls_vs_pub_pct": round(imp_my_ls_vs_pub, 1),
                "n_2opt_improves": n_ls_improves,
                "published_off": len(pub_off),
                "my_off": len(my_off),
                "my_ls_off": len(my2_off),
                "published_runtime": round(rt_pub, 4),
                "my_runtime": round(rt_my, 4),
                "my_ls_runtime": round(rt_my_ls, 4),
            })
            acc[n]["truck"].append(r0)
            acc[n]["pub"].append(mk_pub)
            acc[n]["my"].append(mk_my)
            acc[n]["my_ls"].append(mk_my_ls)
            acc[n]["ls_improves"].append(n_ls_improves)
            L.append(
                f"  seed {seed}: truck={r0:7.1f}  published={mk_pub:7.1f} "
                f"({imp_pub:5.1f}%)  my={mk_my:7.1f} ({imp_my:5.1f}%)  "
                f"my+LS={mk_my_ls:7.1f} ({imp_my_ls_vs_my:+5.2f}%LS)  "
                f"off pub={len(pub_off)}/{n} my={len(my_off)}/{n}  "
                f"myVsPub={imp_my_vs_pub:5.1f}%")
        L.append("")

    # ---- aggregate ----
    L.append("=" * 78)
    L.append("AGGREGATE (mean over seeds per size)")
    L.append("=" * 78)
    summary_rows = []
    for n in SIZES:
        t, p, m, mls, lsim = (acc[n]["truck"], acc[n]["pub"],
                              acc[n]["my"], acc[n]["my_ls"],
                              acc[n]["ls_improves"])
        imp_pub = _mean([(a - b) / a * 100 for a, b in zip(t, p) if a > 0])
        imp_my = _mean([(a - b) / a * 100 for a, b in zip(t, m) if a > 0])
        imp_mvp = _mean([(a - b) / a * 100 for a, b in zip(p, m) if a > 0])
        imp_ls_vs_my = _mean([(a - b) / a * 100
                              for a, b in zip(m, mls) if a > 0])
        imp_ls_vs_pub = _mean([(a - b) / a * 100
                               for a, b in zip(p, mls) if a > 0])
        off_pub = _mean([r["published_off"] for r in raw_rows
                         if r["size"] == n])
        off_my = _mean([r["my_off"] for r in raw_rows if r["size"] == n])
        off_my_ls = _mean([r["my_ls_off"] for r in raw_rows
                           if r["size"] == n])
        avg_ls_improves = _mean(lsim)
        srow = {
            "size": n,
            "n_instances": N_SEEDS,
            "truck_only_makespan": round(_mean(t), 1),
            "published_makespan": round(_mean(p), 1),
            "my_makespan": round(_mean(m), 1),
            "my_ls_makespan": round(_mean(mls), 1),
            "imp_published_vs_truck_pct": round(imp_pub, 1),
            "imp_my_vs_truck_pct": round(imp_my, 1),
            "imp_my_vs_published_pct": round(imp_mvp, 1),
            "imp_my_ls_vs_my_pct": round(imp_ls_vs_my, 2),
            "imp_my_ls_vs_published_pct": round(imp_ls_vs_pub, 1),
            "avg_2opt_improves_per_inst": round(avg_ls_improves, 1),
            "published_offloaded": round(off_pub, 1),
            "my_offloaded": round(off_my, 1),
            "my_ls_offloaded": round(off_my_ls, 1),
            "published_offload_rate_pct": round(off_pub / n * 100, 1),
            "my_offload_rate_pct": round(off_my / n * 100, 1),
            "published_runtime_mean": round(
                _mean([r["published_runtime"] for r in raw_rows
                       if r["size"] == n]), 4),
            "my_runtime_mean": round(
                _mean([r["my_runtime"] for r in raw_rows
                       if r["size"] == n]), 4),
            "my_ls_runtime_mean": round(
                _mean([r["my_ls_runtime"] for r in raw_rows
                       if r["size"] == n]), 4),
        }
        summary_rows.append(srow)
        L.append(
            f"  N={n}: truck={srow['truck_only_makespan']:7.1f} "
            f"published={srow['published_makespan']:7.1f} "
            f"({srow['imp_published_vs_truck_pct']:5.1f}%)  "
            f"my={srow['my_makespan']:7.1f} "
            f"({srow['imp_my_vs_truck_pct']:5.1f}%)  "
            f"my+LS={srow['my_ls_makespan']:7.1f} "
            f"({srow['imp_my_ls_vs_my_pct']:+5.2f}%LS)  "
            f"myVsPub={srow['imp_my_vs_published_pct']:5.1f}%  "
            f"off pub={off_pub:.1f}/{n} my={off_my:.1f}/{n}  "
            f"2opt-moves={avg_ls_improves:.1f}")
    L.append("")

    # ---- write csv ----
    with open(out_raw, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(raw_rows[0].keys()))
        w.writeheader()
        for row in raw_rows:
            w.writerow(row)
    with open(out_summary, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        w.writeheader()
        for row in summary_rows:
            w.writerow(row)

    text = "\n".join(L)
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print(f"\n[raw -> {out_raw}]")
    print(f"[summary -> {out_summary}]")
    print(f"[log -> {out_txt}]")


if __name__ == "__main__":
    main()
