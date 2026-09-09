"""Schneider (2014) E-VRPTW — instance parser + constructive baseline solver.

NOTE (honesty / scope):
- Instances are fetched from a GitHub mirror (EllinorAndRegina/optimizing-the-evrp-using-alns-master-thesis)
  of the Schneider E-VRPTW data. This mirror uses the *100-customer* variant where the file suffix
  (e.g. _21) denotes the NUMBER OF CHARGING STATIONS, NOT the customer count. Schneider's original
  paper instances use 21/33/45/... customers. So our results are NOT directly comparable to the BKS
  table in Schneider (2014) until we (a) confirm which instance variant to use and (b) obtain the
  canonical BKS (from the paper PDF / a literature source).
- The solver below is a *constructive greedy baseline* (feasibility-checked: capacity, time windows,
  battery with full recharge at stations). It is a sanity/feasibility demonstration of the pipeline,
  NOT a competitive metaheuristic, and is NOT yet validated against any BKS.
- Recharge-time convention follows the mirror's parameter `g` (inverse refueling rate): time to
  recharge from soc to full = (Q - soc) * g. Exact Schneider (2014) convention to be confirmed vs PDF.
"""
import os, re, glob, csv, math

HERE = os.path.dirname(os.path.abspath(__file__))
INST_DIR = os.path.join(HERE, "..", "..", "instances", "schneider_evrptw")

def parse_instance(path):
    with open(path) as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    # line 0 = header, skip. trailing param lines start with Q/C/r/g/v/m
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

def solve(inst, seed=0):
    """Constructive greedy: min vehicles (hierarchical), then min distance.
    Feasibility: capacity, time windows (with waiting), battery (full recharge at stations)."""
    P = inst["params"]
    C = P.get("C", 200.0)          # load capacity
    Q = P.get("Q", 79.69)          # battery capacity
    r = P.get("r", 1.0)            # energy per distance
    g = P.get("g", 3.39)           # inverse refueling rate
    v = P.get("v", 1.0)            # speed
    depot = inst["depot"]
    stations = inst["stations"]
    custs = list(inst["customers"])
    # order by earliest deadline, then earliest ready
    custs.sort(key=lambda c: (c["due"], c["ready"]))

    unassigned = set(c["id"] for c in custs)
    cbyid = {c["id"]: c for c in custs}

    def recharge_time(soc):
        return (Q - soc) * g

    def leg_ok(u, w, soc, t):
        """Can we travel u->w (optionally via a station) staying feasible? Return (soc', t', used_station)."""
        d = dist(u, w)
        if soc - d * r >= 0:
            arr = t + d / v
            return soc - d * r, arr, None
        # need a station between u and w
        for st in stations:
            du = dist(u, st); dw = dist(st, w)
            if soc - du * r >= 0 and (Q - dw * r) >= 0:
                arr_st = t + du / v
                soc2 = Q
                t2 = arr_st + recharge_time(soc)  # recharge to full
                arr = t2 + dw / v
                return Q - dw * r, arr, st
        return None

    routes = []
    unserved = 0
    while unassigned:
        # build one route
        route = [depot["id"]]
        load = 0.0
        soc = Q
        t = 0.0
        cur = depot
        feasible_end = True
        while True:
            # pick nearest feasible unassigned customer
            best = None; best_key = None
            for cid in list(unassigned):
                c = cbyid[cid]
                if load + c["demand"] > C + 1e-9:
                    continue
                res = leg_ok(cur, c, soc, t)
                if res is None:
                    continue
                nsoc, narr, st = res
                # service + time window (waiting allowed)
                start = max(narr, c["ready"])
                if start > c["due"] + 1e-9:
                    continue
                t_after = start + c["serv"]
                # back to depot feasibility (battery) from customer
                back = leg_ok(c, depot, nsoc, t_after)
                if back is None:
                    continue
                key = dist(cur, c)
                if best is None or key < best_key:
                    best = (c, st, nsoc, start, t_after, back)
                    best_key = key
            if best is None:
                break
            c, st, nsoc, start, t_after, back = best
            if st is not None:
                route.append(st["id"])
                # update time to station arrival + recharge already in leg_ok nsoc? we approximate: re-append handled by soc
            route.append(c["id"])
            load += c["demand"]
            soc = nsoc
            t = t_after
            cur = c
            unassigned.discard(c["id"])
        # return to depot (close the tour)
        route.append(depot["id"])
        routes.append(route)
        if len(route) == 1:
            # this route assigned no customer -> remaining customers cannot start a feasible route
            unserved = len(unassigned)
            break
        if len(routes) > 200:
            feasible_end = False
            unserved = len(unassigned)
            break
    # compute total distance
    total = 0.0
    node_by_id = {depot["id"]: depot}
    for s in stations:
        node_by_id[s["id"]] = s
    node_by_id.update(cbyid)
    for rt in routes:
        for i in range(len(rt) - 1):
            total += dist(node_by_id[rt[i]], node_by_id[rt[i + 1]])
    return dict(vehicles=len(routes), distance=round(total, 2),
                n_customers=len(custs), n_stations=len(stations),
                unserved=unserved)

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
            res = solve(inst)
        except Exception as e:
            print(f"SKIP {name}: {e}")
            continue
        rows.append([inst["name"], res["n_customers"], res["n_stations"],
                     res["vehicles"], res["distance"], res.get("unserved", 0)])
        print(f"{inst['name']:12s} cust={res['n_customers']:3d} stn={res['n_stations']:2d} "
              f"veh={res['vehicles']:3d} dist={res['distance']:8.1f} unserved={res.get('unserved',0)}")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["instance", "n_customers", "n_stations", "vehicles", "total_distance", "unserved"])
        w.writerows(rows)
    print(f"\nwrote {out} ({len(rows)} rows)")

if __name__ == "__main__":
    main()
