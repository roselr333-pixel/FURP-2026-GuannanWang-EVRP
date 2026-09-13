"""Schneider (2014) E-VRPTW — instance parser + constructive baseline solver.

Provenance notes (verified 2026-09-10):
- Instances were fetched from a GitHub mirror (EllinorAndRegina/optimizing-the-evrp-using-alns-master-thesis).
  I confirmed they are the Schneider ORIGINAL data (byte-identical / whitespace-only diff vs the
  jmanzolli/E-VRPTW "E-VRPTW Instances" folder, which reports Schneider's CPLEX BKS). So the BKS
  comparison in schneider_bks_compare.py is valid; I do NOT need the paper PDF to benchmark.
- The solver is a *constructive greedy baseline* (feasibility-checked: capacity, time windows with
  waiting, battery with full recharge at stations). It is NOT a competitive metaheuristic.
- Key modeling choice: a homogeneous fleet where a vehicle MAY serve several routes (multi-trip),
  returning to the depot and recharging between trips, with the hierarchical objective MINIMISE VEHICLES
  first, then total distance. HONEST CAVEAT (verified 2026-09-10): a constructive greedy cannot globally
  assign customers to multi-trip vehicles (later trips depart too late to catch early time windows), so my
  vehicle count stays well above Schneider's BKS (e.g. c201_21: 15-16 vs 4). The remaining distance gap is
  therefore heuristic-vs-ALNS quality, NOT a modeling mismatch. I report it as such.
- Recharge-time convention: time to recharge from soc to full = (Q - soc) * g (mirror parameter `g`).
"""
import os, re, glob, csv, math, time
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import schneider_improve as SI   # local search on top of the constructive route
INST_DIR = os.path.join(HERE, "..", "..", "instances", "schneider_evrptw")

def parse_instance(path):
    with open(path, encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    params = {}
    data_lines = []
    for ln in lines[1:]:
        if ln[0].isalpha() and ln.split()[0] in ("Q", "C", "r", "g", "v", "m"):
            key = ln.split()[0]
            m = re.search(r"/([\d.]+)/", ln)
            if m:
                params[key] = float(m.group(1))
        else:
            data_lines.append(ln)
    depot = None
    stations = []
    customers = []
    for ln in data_lines:
        p = ln.split()
        sid, typ = p[0], p[1]
        x, y = float(p[2]), float(p[3])
        demand = float(p[4]); ready = float(p[5]); due = float(p[6]); serv = float(p[7])
        node = dict(id=sid, type=typ, x=x, y=y, demand=demand, ready=ready, due=due, serv=serv)
        if typ == "d":
            depot = node
        elif typ == "f":
            stations.append(node)
        elif typ == "c":
            customers.append(node)
    return dict(depot=depot, stations=stations, customers=customers, params=params,
                name=os.path.basename(path).replace(".txt", ""))

def dist(a, b):
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])

def solve(inst, seed=0, multitrip=True, trip_cap=8, max_cust=None,
          improve=True, improve_moves=400, improve_budget=60.0):
    """Constructive greedy for E-VRPTW, followed by local search.

    multitrip=True  -> homogeneous fleet, multi-trip vehicles, MIN vehicles then MIN distance.
    multitrip=False -> legacy single-trip-per-vehicle mode (one route == one vehicle).
    improve=True    -> `schneider_improve.improve_solution` then moves whole trips
                       between vehicles, merges trips, relocates/swaps customers and
                       applies 2-opt, under the same hierarchical objective.
    Feasibility: capacity, time windows (waiting allowed), battery with full recharge
    at stations, and the depot closing time (the horizon).
    """
    P = inst["params"]
    C = P.get("C", 200.0)          # load capacity
    Q = P.get("Q", 79.69)          # battery capacity
    r = P.get("r", 1.0)            # energy per distance
    g = P.get("g", 3.39)           # inverse refueling rate
    v = P.get("v", 1.0)            # speed
    depot = inst["depot"]
    stations = inst["stations"]
    custs = list(inst["customers"])
    custs.sort(key=lambda c: (c["due"], c["ready"]))
    cbyid = {c["id"]: c for c in custs}
    horizon = depot.get("due", float("inf"))   # planning horizon = depot close time

    def recharge_time(soc):
        return (Q - soc) * g

    def leg_ok(u, w, soc, t):
        """Travel u->w (optionally via a station). Return (soc', arrival, used_station) or None."""
        d = dist(u, w)
        if soc - d * r >= 0:
            return soc - d * r, t + d / v, None
        for st in stations:
            du = dist(u, st); dw = dist(st, w)
            if soc - du * r >= 0 and (Q - dw * r) >= 0:
                arr_st = t + du / v
                t2 = arr_st + recharge_time(soc)
                return Q - dw * r, t2 + dw / v, st
        return None

    def build_trip(unassigned, depart_t, max_cust=None, horizon=None):
        """Build one closed route from depot at given departure time.

        When `horizon` (the depot closing time) is given, no customer is added if
        the trip would return to the depot after it — otherwise a vehicle could
        be sent out on a trip that violates the depot's own time window.
        Return (route_ids, served_ids, duration).
        """
        route = [depot["id"]]
        load = 0.0; soc = Q; t = depart_t; cur = depot
        served = []
        while True:
            if max_cust is not None and len(served) >= max_cust:
                break
            best = None; best_key = None
            for cid in sorted(unassigned):  # deterministic: avoid set-iteration hash-order non-determinism
                c = cbyid[cid]
                if load + c["demand"] > C + 1e-9:
                    continue
                res = leg_ok(cur, c, soc, t)
                if res is None:
                    continue
                nsoc, narr, st = res
                start = max(narr, c["ready"])
                if start > c["due"] + 1e-9:
                    continue
                t_after = start + c["serv"]
                back = leg_ok(c, depot, nsoc, t_after)
                if back is None:
                    continue
                if horizon is not None and back[1] > horizon + 1e-9:
                    continue
                key = dist(cur, c)
                if best is None or key < best_key:
                    best = (c, st, nsoc, start, t_after); best_key = key
            if best is None:
                break
            c, st, nsoc, start, t_after = best
            if st is not None:
                route.append(st["id"])
            route.append(c["id"]); load += c["demand"]; soc = nsoc; t = t_after; cur = c
            served.append(c["id"]); unassigned.discard(c["id"])
        back = leg_ok(cur, depot, soc, t)
        if back is not None and back[2] is not None:
            route.append(back[2]["id"])
        route.append(depot["id"])
        duration = (back[1] if back else t) - depart_t
        return route, served, duration

    unassigned = set(c["id"] for c in custs)
    vehicles = []   # each: {"clock": float, "trips": [route_ids,...]}
    unserved = 0
    while unassigned:
        placed = False
        if multitrip and vehicles:
            candidates = []
            for veh in vehicles:
                if len(veh["trips"]) >= trip_cap:
                    continue
                route, served, dur = build_trip(unassigned, veh["clock"],
                                                max_cust, horizon)
                if served and veh["clock"] + dur <= horizon + 1e-9:
                    candidates.append((veh, route, served, dur))
            if candidates:
                # best-fit: reuse the busiest vehicle that still fits (keep others free for early windows)
                candidates.sort(key=lambda x: (-x[0]["clock"], len(x[0]["trips"])))
                veh, route, served, dur = candidates[0]
                veh["trips"].append(route); veh["clock"] += dur
                for cid in served:
                    unassigned.discard(cid)
                placed = True
        if not placed:
            route, served, dur = build_trip(unassigned, 0.0, max_cust, horizon)
            if not served:
                unserved = len(unassigned)
                break
            vehicles.append({"clock": dur, "trips": [route]})
            for cid in served:
                unassigned.discard(cid)

    # total distance
    node_by_id = {depot["id"]: depot}
    for s in stations:
        node_by_id[s["id"]] = s
    node_by_id.update(cbyid)
    total = 0.0
    n_trips = 0
    for veh in vehicles:
        for rt in veh["trips"]:
            n_trips += 1
            for i in range(len(rt) - 1):
                total += dist(node_by_id[rt[i]], node_by_id[rt[i + 1]])
    vehicle_routes = [list(v["trips"]) for v in vehicles]
    cons_vehicles, cons_trips, cons_distance = len(vehicles), n_trips, total

    if improve and vehicle_routes:
        veh = [{"clock": 0.0, "trips": [list(rt) for rt in v]}
               for v in vehicle_routes]
        veh, info = SI.improve_solution(inst, veh, max_moves=improve_moves,
                                        time_budget=improve_budget)
        if info["after"] is not None and info["after"] < (cons_vehicles,
                                                          cons_distance):
            vehicle_routes = [list(v["trips"]) for v in veh]
            total = 0.0
            n_trips = 0
            for rt in [t for v in vehicle_routes for t in v]:
                n_trips += 1
                for i in range(len(rt) - 1):
                    total += dist(node_by_id[rt[i]], node_by_id[rt[i + 1]])

    return dict(vehicles=len(vehicle_routes), trips=n_trips,
                distance=round(total, 2),
                n_customers=len(custs), n_stations=len(stations),
                unserved=unserved, routes=vehicle_routes,
                node_by_id=node_by_id,
                constructive_vehicles=cons_vehicles,
                constructive_trips=cons_trips,
                constructive_distance=round(cons_distance, 2),
                improved=bool(improve))

def main():
    files = sorted(glob.glob(os.path.join(INST_DIR, "*.txt")))
    out = os.path.join(HERE, "..", "results", "schneider_evrptw_baseline.csv")
    rows = []
    for fp in files:
        name = os.path.basename(fp)
        if name.lower() == "readme.txt":
            continue
        try:
            inst = parse_instance(fp)
            t0 = time.perf_counter()
            res = solve(inst)
            elapsed = time.perf_counter() - t0
        except Exception as e:
            print(f"SKIP {name}: {e}")
            continue
        rows.append([inst["name"], res["n_customers"], res["n_stations"],
                     res["vehicles"], res["trips"], res["distance"],
                     round(elapsed, 3), res.get("unserved", 0),
                     res.get("constructive_vehicles", res["vehicles"]),
                     res.get("constructive_distance", res["distance"])])
        print(f"{inst['name']:12s} cust={res['n_customers']:3d} stn={res['n_stations']:2d} "
              f"veh={res['vehicles']:3d} (was {res.get('constructive_vehicles', 0):3d}) "
              f"dist={res['distance']:8.1f} (was {res.get('constructive_distance', 0):8.1f}) "
              f"t={elapsed:6.2f}s unserved={res.get('unserved',0)}")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["instance", "n_customers", "n_stations", "vehicles", "trips",
                    "total_distance", "solve_time_s", "unserved",
                    "constructive_vehicles", "constructive_distance"])
        w.writerows(rows)
    print(f"\nwrote {out} ({len(rows)} rows)")

if __name__ == "__main__":
    main()
