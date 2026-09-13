"""
Local search on top of the Schneider (2014) E-VRPTW constructive solution.

The constructive greedy in `schneider_evrptw.py` opens many more vehicles than
the published best-known solutions (16 vs 4 on c201_21) and builds every trip by
nearest neighbour. This module adds, working on the same
`{"clock", "trips"}` structure:

  * `repair_route` — insert the *cheapest feasible* charging station whenever
    the battery would run out (the constructor only ever tried stations in file
    order, so it can miss a much shorter detour);
  * `eval_route` — walk an explicit route (stations are nodes) and return
    feasibility, distance and end time;
  * `improve_solution` — intra-trip 2-opt plus inter-trip customer relocation
    and swaps, accepting a move only when the lexicographic objective
    **(number of vehicles, total distance)** improves. Emptying a vehicle
    therefore always beats any distance gain, which is Schneider's hierarchical
    objective (vehicles first, then distance).

Every move re-checks capacity, time windows and battery from scratch — a move
that cannot be repaired into a feasible route is rejected.
"""
import math


def dist(a, b):
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])


def nodes_of(inst):
    m = {inst["depot"]["id"]: inst["depot"]}
    for s in inst["stations"]:
        m[s["id"]] = s
    for c in inst["customers"]:
        m[c["id"]] = c
    return m


def _params(inst):
    P = inst["params"]
    return (P.get("C", 200.0), P.get("Q", 79.69), P.get("r", 1.0),
            P.get("g", 3.39), P.get("v", 1.0))


def eval_route(inst, route_ids, depart_t=0.0, nodes=None):
    """Walk an explicit route (stations included as nodes).

    Returns (ok, distance, end_time). ok is False when a capacity, time-window
    or battery constraint is violated.
    """
    C, Q, r, g, v = _params(inst)
    nodes = nodes or nodes_of(inst)
    depot_id = inst["depot"]["id"]
    ids = list(route_ids)
    if not ids or ids[0] != depot_id or ids[-1] != depot_id:
        return False, float("inf"), float("inf")
    load = 0.0
    soc = Q
    t = depart_t
    total = 0.0
    cur = nodes[ids[0]]
    for nid in ids[1:]:
        nxt = nodes[nid]
        d = dist(cur, nxt)
        total += d
        if nxt["type"] == "f":
            t += d / v
            t += (Q - soc) * g          # full recharge (matching the constructor)
            soc = Q
        else:
            if load + nxt["demand"] > C + 1e-9:
                return False, float("inf"), float("inf")
            if soc - d * r < -1e-9:
                return False, float("inf"), float("inf")
            load += nxt["demand"]
            soc -= d * r
            t += d / v
            if t < nxt["ready"]:
                t = nxt["ready"]
            if t > nxt["due"] + 1e-9:
                return False, float("inf"), float("inf")
            t += nxt["serv"]
        cur = nxt
    return True, total, t


def repair_route(inst, route_ids, depart_t=0.0, nodes=None):
    """Insert the cheapest feasible station wherever the battery would run out.

    Returns (route_ids or None, distance, end_time). `None` means the route
    cannot be made feasible by adding stations.
    """
    C, Q, r, g, v = _params(inst)
    nodes = nodes or nodes_of(inst)
    stations = inst["stations"]
    depot_id = inst["depot"]["id"]
    ids = list(route_ids)
    if not ids or ids[0] != depot_id or ids[-1] != depot_id:
        return None, float("inf"), float("inf")
    out = [ids[0]]
    load = 0.0
    soc = Q
    t = depart_t
    total = 0.0
    cur = nodes[ids[0]]
    for nid in ids[1:]:
        nxt = nodes[nid]
        d = dist(cur, nxt)
        if nxt["type"] != "f" and soc - d * r < -1e-9:
            best = None
            for st in stations:
                if st["id"] in out[-1:]:
                    continue
                du = dist(cur, st)
                if soc - du * r < -1e-9:
                    continue
                if Q - dist(st, nxt) * r < -1e-9:
                    continue
                extra = du + dist(st, nxt) - d
                if best is None or extra < best[0]:
                    best = (extra, st, du)
            if best is None:
                return None, float("inf"), float("inf")
            _, st, du = best
            t += du / v
            total += du
            t += (Q - soc) * g
            soc = Q
            out.append(st["id"])
            cur = st
            d = dist(cur, nxt)
        total += d                     # every travelled leg counts
        if nxt["type"] == "f":
            t += d / v
            t += (Q - soc) * g
            soc = Q
        else:
            if load + nxt["demand"] > C + 1e-9:
                return None, float("inf"), float("inf")
            if soc - d * r < -1e-9:
                return None, float("inf"), float("inf")
            load += nxt["demand"]
            soc -= d * r
            t += d / v
            if t < nxt["ready"]:
                t = nxt["ready"]
            if t > nxt["due"] + 1e-9:
                return None, float("inf"), float("inf")
            t += nxt["serv"]
        cur = nxt
        out.append(nid)
    return out, total, t

def _eval_vehicle(inst, veh, nodes):
    """Normalise one vehicle's trips; return (veh', distance) or (None, inf)."""
    clock = 0.0
    trips = []
    total = 0.0
    for rt in veh["trips"]:
        fixed, d, clock = repair_route(inst, rt, clock, nodes)
        if fixed is None:
            return None, float("inf")
        trips.append(fixed)
        total += d
    return {"clock": clock, "trips": trips}, total


def _normalise(inst, vehicles, nodes):
    """Repair every trip; return (vehicles', (n_vehicles, distance)) or (None, None)."""
    new_vehicles = []
    total = 0.0
    for veh in vehicles:
        fixed, d = _eval_vehicle(inst, veh, nodes)
        if fixed is None or not fixed["trips"]:
            return None, None
        new_vehicles.append(fixed)
        total += d
    return new_vehicles, (len(new_vehicles), total)



def improve_solution(inst, vehicles, max_moves=400, time_budget=60.0,
                     verbose=False):
    """Trip-level and customer-level local search under the hierarchical
    objective (vehicles first, total distance second).

    Operators, tried in this order:
      1. move a whole trip to another vehicle   (same distance, can drop a vehicle)
      2. merge two trips into one               (removes a depot round-trip)
      3. relocate one customer between trips
      4. swap two customers between trips
      5. 2-opt inside one trip

    A move is accepted only when the lexicographic key improves. Only the
    vehicles a move touches are re-evaluated, which keeps the search fast enough
    to run over all 92 instances. A move that would touch two trips of the *same*
    vehicle updates that one vehicle object, so no customer is duplicated.
    """
    import time as _time

    nodes = nodes_of(inst)
    depot_id = inst["depot"]["id"]
    t_start = _time.perf_counter()

    parts = []                       # list of (vehicle, distance)
    for veh in vehicles:
        fixed, d = _eval_vehicle(inst, veh, nodes)
        if fixed is None or not fixed["trips"]:
            return vehicles, {"before": None, "after": None, "moves": 0}
        parts.append((fixed, d))
    key = (len(parts), sum(d for _, d in parts))
    before = key
    moves = 0

    def try_accept(drop, touched):
        """`touched`: {vehicle index: new trip list}; empty lists are dropped."""
        nonlocal parts, key, moves
        kept = [p for i, p in enumerate(parts) if i not in drop]
        added = []
        for trips in touched.values():
            if not trips:
                continue
            fixed, d = _eval_vehicle(inst, {"clock": 0.0, "trips": trips}, nodes)
            if fixed is None or not fixed["trips"]:
                return False
            added.append((fixed, d))
        cand = kept + added
        ckey = (len(cand), sum(d for _, d in cand))
        if ckey >= key:
            return False
        parts, key, moves = cand, ckey, moves + 1
        return True

    def _touched(vi, vj):
        t = {vi: [list(x) for x in parts[vi][0]["trips"]]}
        if vj != vi:
            t[vj] = [list(x) for x in parts[vj][0]["trips"]]
        return t

    def _trips(vi, ti):
        return list(parts[vi][0]["trips"][ti])

    def scan_move_trip():
        for vi in range(len(parts)):
            for ti in range(len(parts[vi][0]["trips"])):
                for vj in range(len(parts)):
                    if vj == vi:
                        continue
                    n_vj = len(parts[vj][0]["trips"])
                    for pos in range(n_vj + 1):
                        touched = _touched(vi, vj)
                        trip = touched[vi].pop(ti)
                        touched[vj].insert(pos, trip)
                        if try_accept({vi, vj}, touched):
                            return True
        return False

    def scan_merge_trips():
        for vi in range(len(parts)):
            for ti in range(len(parts[vi][0]["trips"])):
                for vj in range(vi, len(parts)):
                    for tj in range(len(parts[vj][0]["trips"])):
                        if vi == vj and ti >= tj:
                            continue
                        a = [n for n in _trips(vi, ti) if nodes[n]["type"] == "c"]
                        b = [n for n in _trips(vj, tj) if nodes[n]["type"] == "c"]
                        for order in (a + b, b + a):
                            touched = _touched(vi, vj)
                            touched[vi][ti] = [depot_id] + order + [depot_id]
                            touched[vj].pop(tj)
                            if try_accept({vi, vj}, touched):
                                return True
        return False

    def scan_relocate():
        for vi in range(len(parts)):
            for ti in range(len(parts[vi][0]["trips"])):
                rt = parts[vi][0]["trips"][ti]
                for pi, nid in enumerate(rt):
                    if nodes[nid]["type"] != "c":
                        continue
                    for vj in range(len(parts)):
                        for tj in range(len(parts[vj][0]["trips"])):
                            if vi == vj and ti == tj:
                                continue
                            rt2 = parts[vj][0]["trips"][tj]
                            for ins in range(1, len(rt2)):
                                touched = _touched(vi, vj)
                                touched[vi][ti] = rt[:pi] + rt[pi + 1:]
                                touched[vj][tj] = rt2[:ins] + [nid] + rt2[ins:]
                                if try_accept({vi, vj}, touched):
                                    return True
        return False

    def scan_swap():
        for vi in range(len(parts)):
            for ti in range(len(parts[vi][0]["trips"])):
                rt = parts[vi][0]["trips"][ti]
                for pi, a in enumerate(rt):
                    if nodes[a]["type"] != "c":
                        continue
                    for vj in range(vi, len(parts)):
                        for tj in range(len(parts[vj][0]["trips"])):
                            if vi == vj and ti == tj:
                                continue
                            rt2 = parts[vj][0]["trips"][tj]
                            for pj, b in enumerate(rt2):
                                if nodes[b]["type"] != "c":
                                    continue
                                touched = _touched(vi, vj)
                                r1, r2 = list(rt), list(rt2)
                                r1[pi], r2[pj] = b, a
                                touched[vi][ti] = r1
                                touched[vj][tj] = r2
                                if try_accept({vi, vj}, touched):
                                    return True
        return False

    def scan_two_opt():
        for vi in range(len(parts)):
            for ti in range(len(parts[vi][0]["trips"])):
                rt = parts[vi][0]["trips"][ti]
                for i in range(1, len(rt) - 2):
                    for j in range(i + 1, len(rt) - 1):
                        cand_rt = rt[:i] + rt[i:j + 1][::-1] + rt[j + 1:]
                        if cand_rt == rt:
                            continue
                        touched = _touched(vi, vi)
                        touched[vi][ti] = cand_rt
                        if try_accept({vi}, touched):
                            return True
        return False

    operators = [scan_move_trip, scan_merge_trips, scan_relocate, scan_swap,
                 scan_two_opt]
    while moves < max_moves and _time.perf_counter() - t_start < time_budget:
        if not any(op() for op in operators):
            break

    cur_vehicles = [v for v, _ in parts]
    info = {"before": before, "after": key, "moves": moves,
            "customers": sum(1 for v, _ in parts for t in v["trips"]
                             for n in t if nodes[n]["type"] == "c")}
    if verbose:
        print(f"  improve: {before} -> {key} in {moves} moves")
    return cur_vehicles, info
