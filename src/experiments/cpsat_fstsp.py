"""
Exact optimum of the FSTSP truck-drone model by CP-SAT (OR-Tools), for small n.

Why this module exists
----------------------
The reports repeatedly note that "how far the heuristic is from the optimum" is
not quantified, because no exact solver existed for the collaborative problem.
This module provides one, so the gap can be stated on small instances.

The model both the optimum and the heuristics use
------------------------------------------------
Both are defined on the same physically valid model:
  * each sortie launches at a truck node i, serves 1-2 customers, and is
    recovered at a later truck node j (i before j on the truck route);
  * a sortie's flight length must not exceed the drone range R_D;
  * the drone is serial and carried by the truck: the next sortie cannot launch
    before the previous one has been recovered, and the launch node cannot be a
    node the truck has already passed;
  * the truck waits at a recovery node until its sortie lands.

`clean_simulate` below is an independent implementation of that model.
`week07_fstsp_repro.fstsp_simulate` enforces the same rules; the nested-sortie
gap it used to have (sorties could overlap because the drone's return was never
checked) was fixed on 2026-09-13, see
`docs/analysis/evaluator_physical_fix_note_en.md`.

Contents
--------
  fstsp_makespan_clean(inst, route, trips)   physical evaluator (inf if invalid)
  clean_greedy(inst, max_cust)               my V2 greedy restricted to the model
  solve_exact(inst, max_cust, ...)           CP-SAT exact optimum + solution

Run (self-test):
  python src/experiments/cpsat_fstsp.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import week06_ground_air_evrp_tw as w6

V_T = w6.V_T
V_D = w6.V_D
SERVICE = w6.SERVICE
R_D = w6.R_D

INF = float("inf")


# ---------------------------------------------------------------------------
# physical (clean) evaluator
# ---------------------------------------------------------------------------
def _lpos(route, node):
    return 0 if node == 0 else route.index(node)


def _rpos(route, node):
    return len(route) - 1 if node == 0 else route.index(node)


def clean_simulate(inst, route, trips, rd=R_D):
    """Truck arrival times for a PHYSICALLY VALID sortie set.

    Returns (ok, arr). ok is False if the sortie set is not a valid serial plan
    (launch not before recover, range exceeded, or a sortie launched before the
    drone is back on the truck)."""
    arr = [0.0] * len(route)
    for p in range(1, len(route)):
        arr[p] = arr[p - 1] + w6.dist(inst, route[p - 1], route[p]) / V_T \
            + (SERVICE if route[p] != 0 else 0.0)

    ts = sorted(trips, key=lambda t: _lpos(route, t[0]))
    drone_free = 0.0
    for ln, cs, rn in ts:
        i_pos = _lpos(route, ln)
        j_pos = _rpos(route, rn)
        cl = list(cs) if isinstance(cs, (list, tuple)) else [cs]
        if i_pos >= j_pos:
            return False, None
        legs = [ln] + cl + [rn]
        d = sum(w6.dist(inst, legs[p], legs[p + 1])
                for p in range(len(legs) - 1))
        if d > rd + 1e-9:
            return False, None
        # the drone must be back on the truck before the truck reaches the
        # launch node, otherwise the launch node is behind the truck
        if drone_free > arr[i_pos] + 1e-9:
            return False, None
        flight = d / V_D + SERVICE * len(cl)
        landing = arr[i_pos] + flight
        recovery = max(arr[j_pos], landing)
        wait = recovery - arr[j_pos]
        if wait > 0:
            for p in range(j_pos, len(arr)):
                arr[p] += wait
        drone_free = recovery
    return True, arr


def fstsp_makespan_clean(inst, route, trips, rd=R_D):
    """Physical FSTSP completion time, or +inf if the plan is not valid."""
    ok, arr = clean_simulate(inst, route, trips, rd)
    return arr[-1] if ok else INF


# ---------------------------------------------------------------------------
# my V2 greedy, restricted to the physical model
# ---------------------------------------------------------------------------
def clean_greedy(inst, max_cust=2, rd=R_D):
    """Route-and-reassign greedy (same loop as my_v2_param) but every candidate
    is checked with the physical evaluator, so the result is always a valid
    serial plan (no nested/overlapping sorties)."""
    all_c = list(inst["customers"].keys())
    route = [0] + w6.nn_order(inst, all_c) + [0]
    trips = []
    offloaded = set()
    protected = set()

    while True:
        base = fstsp_makespan_clean(inst, route, trips, rd)
        best = None
        for i in range(len(route) - 1):
            for j in range(i + 2, len(route)):
                ln, rn = route[i], route[j]
                cands = [route[p] for p in range(i + 1, j)
                         if route[p] != 0 and route[p] not in offloaded
                         and route[p] not in protected]
                if not cands:
                    continue
                subsets = [(c,) for c in cands]
                if max_cust >= 2:
                    for a in range(len(cands)):
                        for b in range(a + 1, len(cands)):
                            subsets.append((cands[a], cands[b]))
                            subsets.append((cands[b], cands[a]))
                for custs in subsets:
                    legs = [ln] + list(custs) + [rn]
                    d = sum(w6.dist(inst, legs[p], legs[p + 1])
                            for p in range(len(legs) - 1))
                    if d > rd + 1e-9:
                        continue
                    new_route = [x for x in route if x not in custs]
                    m = fstsp_makespan_clean(inst, new_route,
                                             trips + [(ln, custs, rn)], rd)
                    if m == INF:
                        continue
                    gain = base - m
                    if gain > 1e-9 and (best is None or gain > best[0]):
                        best = (gain, ln, custs, rn)
        if best is None:
            break
        _, ln, custs, rn = best
        for c in custs:
            offloaded.add(c)
        protected.add(ln)
        protected.add(rn)
        trips.append((ln, custs, rn))
        route = [x for x in route if x not in custs]
    return route, trips, offloaded


# ---------------------------------------------------------------------------
# CP-SAT exact model
# ---------------------------------------------------------------------------
def _candidate_sorties(inst, max_cust, rd):
    """All (launch, customers_tuple, recover, distance) with distance <= rd.

    Launch nodes are the depot (0) or a customer; recover nodes are a customer
    or the end depot (n+1). Order within a two-customer sortie is material
    (it changes the flight length), so both orders are enumerated."""
    n = inst["n"]
    C = list(inst["customers"].keys())
    end = n + 1

    def D(a, b):
        aa = 0 if a == end else a
        bb = 0 if b == end else b
        return w6.dist(inst, aa, bb)

    out = []
    for i in [0] + C:
        for j in C + [end]:
            if j == i:
                continue
            pool = [c for c in C if c != i and c != j]
            for c1 in pool:
                d = D(i, c1) + D(c1, j)
                if d <= rd + 1e-9:
                    out.append((i, (c1,), j, d))
            if max_cust >= 2:
                for c1 in pool:
                    for c2 in pool:
                        if c1 == c2:
                            continue
                        d = D(i, c1) + D(c1, c2) + D(c2, j)
                        if d <= rd + 1e-9:
                            out.append((i, (c1, c2), j, d))
    return out


def solve_exact(inst, max_cust=2, rd=R_D, time_limit=120.0, num_workers=8,
                log=False, upper_bound=None):
    """Exact minimum completion time of the physical FSTSP model.

    `upper_bound` (a makespan in real units) pins the objective at or below a
    known heuristic value, which prunes the search a lot.

    Returns a dict with: makespan (None if no solution found), proven (whether
    the optimum was proved), route, trips, status, wall_s, bound, n_sorties.
    The truck route is [0, ...customers..., 0]; trips are (launch, custs, recover).
    """
    from ortools.sat.python import cp_model

    n = inst["n"]
    C = list(inst["customers"].keys())
    end = n + 1
    SC = 100

    def D(a, b):
        aa = 0 if a == end else a
        bb = 0 if b == end else b
        return w6.dist(inst, aa, bb)

    sorties = _candidate_sorties(inst, max_cust, rd)
    model = cp_model.CpModel()
    UB = 10 ** 7

    arcs = [(i, j) for i in range(0, n + 1) for j in range(1, n + 2) if i != j]
    x = {(i, j): model.NewBoolVar(f"x_{i}_{j}") for (i, j) in arcs}

    y = {}
    for c in C:
        y[c] = model.NewBoolVar(f"y_{c}")
        model.Add(y[c] == sum(x[(c, j)] for j in range(1, n + 2) if j != c))
        model.Add(y[c] == sum(x[(i, c)] for i in range(0, n + 1) if i != c))
    model.Add(sum(x[(0, j)] for j in range(1, n + 2)) == 1)
    model.Add(sum(x[(i, end)] for i in range(0, n + 1)) == 1)

    u = {v: model.NewIntVar(0, n + 1, f"u_{v}") for v in range(0, n + 2)}
    model.Add(u[0] == 0)
    for (i, j) in arcs:
        model.Add(u[j] >= u[i] + 1).OnlyEnforceIf(x[(i, j)])

    t = {v: model.NewIntVar(0, UB, f"t_{v}") for v in range(0, n + 2)}
    model.Add(t[0] == 0)
    # t[j] >= travel, NOT == : the truck may have to WAIT at a recovery node
    # until the drone lands, so slack between the lower bound and the actual
    # arrival time is exactly the waiting time. Minimising t[end] keeps every t
    # as tight as the waits allow.
    for (i, j) in arcs:
        s = int(round(D(i, j) / V_T * SC)) + (SERVICE * SC if j in C else 0)
        model.Add(t[j] >= t[i] + s).OnlyEnforceIf(x[(i, j)])

    q = [model.NewBoolVar(f"q{k}") for k in range(len(sorties))]
    launch = {v: [] for v in range(0, n + 2)}
    recover = {v: [] for v in range(0, n + 2)}
    launch_sum = {v: model.NewIntVar(0, n, f"ls_{v}") for v in range(0, n + 2)}
    recover_sum = {v: model.NewIntVar(0, n, f"rs_{v}") for v in range(0, n + 2)}
    Lk = [model.NewIntVar(0, UB, f"L{k}") for k in range(len(sorties))]

    for k, (i, cs, j, d) in enumerate(sorties):
        launch[i].append(q[k])
        recover[j].append(q[k])
        fk = int(round(d / V_D * SC)) + SERVICE * len(cs) * SC
        model.Add(u[j] >= u[i] + 1).OnlyEnforceIf(q[k])
        model.Add(Lk[k] >= t[i]).OnlyEnforceIf(q[k])
        model.Add(t[j] >= Lk[k] + fk).OnlyEnforceIf(q[k])
        if i in C:
            model.Add(y[i] == 1).OnlyEnforceIf(q[k])
        if j in C:
            model.Add(y[j] == 1).OnlyEnforceIf(q[k])

    for c in C:
        model.Add(y[c] + sum(q[k] for k, s in enumerate(sorties)
                             if c in s[1]) == 1)

    for v in range(0, n + 2):
        model.Add(launch_sum[v] == sum(launch[v]))
        model.Add(recover_sum[v] == sum(recover[v]))

    # single serial drone: at most one airborne sortie at any point of the
    # route. airin[v] = airborne when the truck arrives at v; air[v] = airborne
    # when the truck leaves v. recover only if airborne; launch only if on board.
    airin = {v: model.NewBoolVar(f"ai_{v}") for v in range(0, n + 2)}
    air = {v: model.NewBoolVar(f"a_{v}") for v in range(0, n + 2)}
    model.Add(airin[0] == 0)
    for (i, j) in arcs:
        model.Add(airin[j] == air[i]).OnlyEnforceIf(x[(i, j)])
    for v in range(0, n + 2):
        model.Add(recover_sum[v] <= airin[v])
        model.Add(launch_sum[v] <= 1 - airin[v] + recover_sum[v])
        model.Add(air[v] == airin[v] + launch_sum[v] - recover_sum[v])
    model.Add(air[end] == 0)

    if upper_bound is not None:
        model.Add(t[end] <= int(round(upper_bound * SC)))

    model.Minimize(t[end])

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = num_workers
    if not log:
        solver.parameters.log_search_progress = False
    t0 = time.perf_counter()
    status = solver.Solve(model)
    wall = time.perf_counter() - t0

    name = solver.StatusName(status)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"makespan": None, "proven": False, "route": None, "trips": None,
                "status": name, "wall_s": round(wall, 2), "bound": None,
                "n_sorties": len(sorties)}

    # reconstruct the truck route
    succ = {}
    for (i, j) in arcs:
        if solver.Value(x[(i, j)]) == 1:
            succ[i] = j
    route = [0]
    while route[-1] != end:
        route.append(succ[route[-1]])
    route = [0 if v == end else v for v in route]

    trips = []
    for k, (i, cs, j, d) in enumerate(sorties):
        if solver.Value(q[k]) == 1:
            trips.append((i, cs, 0 if j == end else j))

    mk = solver.ObjectiveValue() / SC
    bound = solver.BestObjectiveBound() / SC
    return {"makespan": mk, "proven": status == cp_model.OPTIMAL,
            "route": route, "trips": trips, "status": name,
            "wall_s": round(wall, 2), "bound": bound,
            "n_sorties": len(sorties)}


def _main():
    """Self-test: exact optimum must be <= every heuristic and the CP-SAT
    solution must re-evaluate (physically) to its own objective."""
    import week06_ground_air_evrp_tw as _w6
    for n in (8, 10):
        for seed in (20260720, 20260721):
            inst = _w6.make_instance(n, seed=seed)
            res = solve_exact(inst, time_limit=30, num_workers=8)
            gr, gt, _ = clean_greedy(inst, max_cust=2)
            gk = fstsp_makespan_clean(inst, gr, gt)
            gc1, gt1, _ = clean_greedy(inst, max_cust=1)
            g1k = fstsp_makespan_clean(inst, gc1, gt1)
            chk = (fstsp_makespan_clean(inst, res["route"], res["trips"])
                   if res["route"] else None)
            print(f"n={n} seed={seed}: OPT={res['makespan']} "
                  f"({res['status']}, {res['wall_s']}s, "
                  f"{res['n_sorties']} cand) | clean_cap2={gk:.1f} "
                  f"clean_cap1={g1k:.1f} | cross-check={chk}")
            assert res["route"] is None or abs(chk - res["makespan"]) < 1e-6, \
                "CP-SAT solution does not re-evaluate to its objective"
            assert res["makespan"] <= gk + 1e-6, "OPT > cap2 heuristic!"
            assert res["makespan"] <= g1k + 1e-6, "OPT > cap1 heuristic!"


if __name__ == "__main__":
    _main()
