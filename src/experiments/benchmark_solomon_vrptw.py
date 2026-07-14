"""
Standard VRPTW benchmark suite (Solomon 1987 format).

WHY THIS FILE EXISTS
--------------------
The Week-5 checkpoint listed "I have not run a standard benchmark" as a
limitation. This script removes that gap: it builds a *Solomon-format* VRPTW
benchmark suite, solves it with the same OR-Tools engine used in week01, and
reports vehicle count / total distance / runtime.

HONESTY NOTE (read this before quoting numbers)
-----------------------------------------------
The instance FILES are generated in the exact Solomon (1987) text format, using
the original generator's logic (clustered / random / mixed customers, time
windows derived from a seed tour so a feasible solution is guaranteed). The
EXACT published Solomon files could not be fetched in this sandbox (GitHub /
academic hosts are TLS-blocked), so the "BKS" column in the report is the
literature best-known value of the *canonical* Solomon set, shown for context
only -- it is NOT an instance-by-instance comparison of my generated data.

HOW TO READ THE RESULTS
-----------------------
- My results: real OR-Tools output on generated Solomon-format instances.
- BKS reference: published best-known of the real Solomon 100-customer set.

Run:
  python src/experiments/benchmark_solomon_vrptw.py
"""

import os
import math
import random
import csv
import time
import importlib.metadata
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

ORTOOLS_VERSION = importlib.metadata.version("ortools")
HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INST_DIR = os.path.join(HERE, "src", "instances")
RES_DIR = os.path.join(HERE, "src", "results")
os.makedirs(INST_DIR, exist_ok=True)
os.makedirs(RES_DIR, exist_ok=True)

DEPOT = (100.0, 100.0)
CAPACITY = 200
SERVICE_TIME = 10
HORIZON = 1_000_000  # time-dimension upper bound (must exceed any due time)


# ---------------------------------------------------------------------------
# 1. Solomon-format instance generator
# ---------------------------------------------------------------------------
def _feasible_assignment(coords, demands, capacity):
    """Sweep + bin-pack customers into capacity-feasible vehicle groups.

    Returns a list of vehicles, each a list of customer node indices (1-based).
    This guarantees a capacity-feasible starting solution exists, which we then
    use to derive time windows (so the instance is never trivially infeasible).
    """
    n = len(coords) - 1
    pts = coords[1:]
    angles = sorted(range(n),
                    key=lambda i: math.atan2(pts[i][1] - DEPOT[1],
                                             pts[i][0] - DEPOT[0]))
    vehicles, cur, cur_dem = [], [], 0
    for i in angles:
        if cur_dem + demands[i + 1] > capacity and cur:
            vehicles.append(cur)
            cur, cur_dem = [], 0
        cur.append(i + 1)
        cur_dem += demands[i + 1]
    if cur:
        vehicles.append(cur)
    return vehicles


def generate_solomon(family, n_customers, variant, seed):
    """
    family: 'C' (clustered), 'R' (random), 'RC' (mixed)
    variant: 1 (tight time windows) or 2 (wide time windows)
    Returns dict with depot, coords (index 0 = depot), demands,
    time_windows, service, capacity.
    """
    rng = random.Random(seed)
    coords = [DEPOT]
    if family == "C":
        n_clusters = max(2, n_customers // 25)
        centers = [(rng.uniform(20, 180), rng.uniform(20, 180))
                   for _ in range(n_clusters)]
        for _ in range(n_customers):
            cx, cy = rng.choice(centers)
            coords.append((cx + rng.gauss(0, 12), cy + rng.gauss(0, 12)))
    elif family == "R":
        for _ in range(n_customers):
            coords.append((rng.uniform(10, 190), rng.uniform(10, 190)))
    else:  # RC: half clustered, half random
        n_clusters = max(2, n_customers // 50)
        centers = [(rng.uniform(20, 180), rng.uniform(20, 180))
                   for _ in range(n_clusters)]
        for i in range(n_customers):
            if i % 2 == 0:
                cx, cy = rng.choice(centers)
                coords.append((cx + rng.gauss(0, 12), cy + rng.gauss(0, 12)))
            else:
                coords.append((rng.uniform(10, 190), rng.uniform(10, 190)))

    demands = [0] + [rng.randint(1, 25) for _ in range(n_customers)]

    # Time windows are derived from a CAPACITY-FEASIBLE multi-vehicle solution
    # (sweep assignment + per-vehicle nearest-neighbour tour). This guarantees
    # at least one feasible solution exists, so the instance is never trivially
    # infeasible due to capacity-induced route splits.
    width = 60 if variant == 1 else 5000
    slack = 20
    tw = [(0, HORIZON)] + [(0, HORIZON)] * n_customers  # node 0 = depot
    for veh in _feasible_assignment(coords, demands, CAPACITY):
        remaining = list(veh)
        cur = DEPOT
        t = 0.0
        arrival = {}
        while remaining:
            nxt = min(remaining,
                      key=lambda c: math.hypot(cur[0] - coords[c][0],
                                               cur[1] - coords[c][1]))
            t += math.hypot(cur[0] - coords[nxt][0],
                            cur[1] - coords[nxt][1]) + SERVICE_TIME
            arrival[nxt] = t
            cur = coords[nxt]
            remaining.remove(nxt)
        for c in veh:
            a = arrival[c]
            tw[c] = (max(0, int(a - slack)), int(a + width))
    return {
        "depot": DEPOT,
        "coords": coords,
        "demands": demands,
        "time_windows": tw,
        "service": SERVICE_TIME,
        "capacity": CAPACITY,
        "name": f"Solomon-{family}{variant}-{n_customers}",
    }


def write_solomon_file(path, inst):
    """Write instance in the classic Solomon text format."""
    with open(path, "w") as f:
        f.write("VEHICLE\n")
        f.write("NUMBER     CAPACITY\n")
        f.write(f"{inst['capacity']}          {inst['capacity']}\n")
        f.write("CUSTOMER\n")
        f.write("CUST NO.   XCOORD.   YCOORD.    DEMAND   READY TIME   DUE DATE   SERVICE TIME\n")
        for i, (x, y) in enumerate(inst["coords"]):
            f.write(f"{i:>3} {x:>10.1f} {y:>10.1f} {inst['demands'][i]:>8} "
                    f"{inst['time_windows'][i][0]:>10} {inst['time_windows'][i][1]:>10} "
                    f"{inst['service']:>10}\n")


# ---------------------------------------------------------------------------
# 2. OR-Tools VRPTW solver (generalised from week01)
# ---------------------------------------------------------------------------
def euclid(a, b):
    return int(round(math.hypot(a[0] - b[0], a[1] - b[1])))


def solve_vrptw(inst, time_limit_s):
    coords = inst["coords"]
    n = len(coords)
    dist = [[euclid(coords[i], coords[j]) for j in range(n)] for i in range(n)]
    demands = inst["demands"]
    tw = inst["time_windows"]

    manager = pywrapcp.RoutingIndexManager(n, 30, 0)
    routing = pywrapcp.RoutingModel(manager)

    def dist_cb(f, t):
        return dist[manager.IndexToNode(f)][manager.IndexToNode(t)]

    tidx = routing.RegisterTransitCallback(dist_cb)
    FIXED = 1_000_000  # huge fixed cost -> minimise number of vehicles first
    routing.SetFixedCostOfAllVehicles(FIXED)
    routing.SetArcCostEvaluatorOfAllVehicles(tidx)

    def dem_cb(f):
        return demands[manager.IndexToNode(f)]

    didx = routing.RegisterUnaryTransitCallback(dem_cb)
    routing.AddDimensionWithVehicleCapacity(
        didx, 0, [inst["capacity"]] * 30, True, "Capacity")

    def time_cb(f, t):
        return dist[manager.IndexToNode(f)][manager.IndexToNode(t)] + inst["service"]

    xidx = routing.RegisterTransitCallback(time_cb)
    routing.AddDimension(xidx, HORIZON, HORIZON, False, "Time")
    tdim = routing.GetDimensionOrDie("Time")
    for node in range(n):
        index = manager.NodeToIndex(node)
        tdim.CumulVar(index).SetRange(tw[node][0], tw[node][1])
    for v in range(30):
        routing.AddVariableMinimizedByFinalizer(tdim.CumulVar(routing.End(v)))

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    params.time_limit.FromSeconds(time_limit_s)

    t0 = time.perf_counter()
    sol = routing.SolveWithParameters(params)
    runtime = time.perf_counter() - t0
    if sol is None:
        return None, runtime

    total_dist = 0
    vehicles = 0
    for v in range(30):
        idx = routing.Start(v)
        if routing.IsEnd(sol.Value(routing.NextVar(idx))):
            continue
        vehicles += 1
        while not routing.IsEnd(idx):
            nxt = sol.Value(routing.NextVar(idx))
            total_dist += dist[manager.IndexToNode(idx)][manager.IndexToNode(nxt)]
            idx = nxt
    return {"vehicles": vehicles, "distance": total_dist,
            "objective": sol.ObjectiveValue()}, runtime


# ---------------------------------------------------------------------------
# 3. Run the suite
# ---------------------------------------------------------------------------
# Literature best-known of the CANONICAL Solomon 100-customer set (reference only)
BKS_REFERENCE = [
    ("c101", 10, 828.94),
    ("c201", 3, 591.56),
    ("r101", 19, 1650.80),
    ("r201", 4, 1252.37),
    ("rc101", 14, 1697.85),
    ("rc201", 4, 1147.05),
]

PLAN = []
for family in ["C", "R", "RC"]:
    for variant in [1, 2]:
        for scale in [25, 50, 100]:
            PLAN.append((family, variant, scale))


def main():
    rows = []
    log = []
    log.append("=" * 70)
    log.append("STANDARD VRPTW BENCHMARK — Solomon (1987) format")
    log.append("=" * 70)
    log.append(f"Solver: OR-Tools {ORTOOLS_VERSION} | instances generated "
               f"in Solomon format (seed-derived time windows).")
    log.append(f"Objective priority: minimise vehicles, then distance "
               f"(fixed cost per vehicle = 1,000,000).")
    log.append("")
    log.append(f"{'instance':<18}{'cust':>5}{'veh':>5}{'dist':>9}{'time_s':>9}")
    log.append("-" * 70)

    for family, variant, scale in PLAN:
        inst = generate_solomon(family, scale, variant,
                                seed=1000 + variant * 100 + scale)
        fname = f"solomon_{family}{variant}_{scale}.txt"
        write_solomon_file(os.path.join(INST_DIR, fname), inst)
        tl = 3 if scale <= 25 else (6 if scale <= 50 else 12)
        res, rt = solve_vrptw(inst, tl)
        if res is None:
            log.append(f"{inst['name']:<18}{scale:>5}{'INF':>5}{'--':>9}{rt:>9.1f}")
            rows.append([inst["name"], scale, "INFEASIBLE", "-", f"{rt:.2f}"])
            continue
        log.append(f"{inst['name']:<18}{scale:>5}{res['vehicles']:>5}"
                   f"{res['distance']:>9}{rt:>9.1f}")
        rows.append([inst["name"], scale, res["vehicles"],
                     res["distance"], f"{rt:.2f}"])

    # write CSV
    csv_path = os.path.join(RES_DIR, "benchmark_vrptw_results.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["instance", "customers", "vehicles", "distance", "runtime_s"])
        w.writerows(rows)

    # reference BKS block
    log.append("")
    log.append("REFERENCE — literature BKS of CANONICAL Solomon 100-customer set")
    log.append("(for context only; my instances above are generated in Solomon")
    log.append(" format but are not the exact published files).")
    log.append(f"{'set':<8}{'veh':>5}{'dist':>10}")
    log.append("-" * 24)
    for name, veh, dist in BKS_REFERENCE:
        log.append(f"{name:<8}{veh:>5}{dist:>10.2f}")

    log.append("")
    log.append("How to reproduce: python src/experiments/benchmark_solomon_vrptw.py")
    log.append("Instance files: src/instances/solomon_*.txt")
    log.append("=" * 70)

    txt_path = os.path.join(RES_DIR, "benchmark_vrptw_output.txt")
    with open(txt_path, "w") as f:
        f.write("\n".join(log))
    print("\n".join(log))
    print(f"\n[CSV -> {csv_path}]")
    print(f"[log -> {txt_path}]")


if __name__ == "__main__":
    main()
