"""
Official Solomon VRPTW benchmark, solved with OR-Tools and compared to the
published Best-Known Solutions (BKS).

Unlike `benchmark_solomon_vrptw.py` (which generated Solomon-*format* instances
locally because the network was blocked at the time), this script downloads the
**official** Solomon 100-customer instances from the PyVRP/Instances repository,
which ships each instance together with its published optimal/best-known
solution (the `.sol` file, whose `Cost` line is the BKS distance).

For every instance we:
  1. download & cache the official `.vrp` (instance) and `.sol` (BKS) files,
  2. parse the `.vrp` with `vrplib` (TSPLIB-style VRPTW format),
  3. solve it with our OR-Tools VRPTW engine (PATH_CHEAPEST_ARC + Guided Local
     Search, with a per-instance time limit),
  4. read the official BKS distance and vehicle count from the `.sol`,
  5. report our distance / vehicles and the gap to BKS.

Distances follow the Solomon convention (real Euclidean distance). OR-Tools is
an integer solver, so we scale coordinates' distances by DIST_SCALE (=10, one
decimal place, matching the one-decimal BKS costs) and divide back when
reporting.

Run:
    python src/experiments/benchmark_official_solomon.py
"""

import csv
import math
import os
import urllib.request

import vrplib
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INSTANCE_DIR = os.path.join(REPO_ROOT, "src", "instances", "official_solomon")
RESULTS_DIR = os.path.join(REPO_ROOT, "src", "results")
CSV_PATH = os.path.join(RESULTS_DIR, "benchmark_official_solomon_results.csv")
LOG_PATH = os.path.join(RESULTS_DIR, "benchmark_official_solomon_output.txt")

BASE_URL = "https://raw.githubusercontent.com/PyVRP/Instances/main/VRPTW/Solomon/"

DIST_SCALE = 10          # integer scaling for OR-Tools (one decimal precision)
TIME_LIMIT_S = 10        # per-instance OR-Tools search time limit

# The classic 56-instance Solomon set (100 customers each).
FAMILIES = {
    "C1":  [f"C10{i}" for i in range(1, 10)],                 # C101..C109
    "C2":  [f"C20{i}" for i in range(1, 9)],                  # C201..C208
    "R1":  [f"R10{i}" for i in range(1, 10)] + ["R110", "R111", "R112"],
    "R2":  [f"R20{i}" for i in range(1, 10)] + ["R210", "R211"],
    "RC1": [f"RC10{i}" for i in range(1, 9)],                 # RC101..RC108
    "RC2": [f"RC20{i}" for i in range(1, 9)],                 # RC201..RC208
}
ALL_INSTANCES = [n for group in FAMILIES.values() for n in group]


# --------------------------------------------------------------------------- #
# Download / cache
# --------------------------------------------------------------------------- #
def _download(name, ext):
    """Download <name>.<ext> into INSTANCE_DIR (cached). Return local path."""
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    local = os.path.join(INSTANCE_DIR, f"{name}.{ext}")
    if os.path.exists(local) and os.path.getsize(local) > 0:
        return local
    url = f"{BASE_URL}{name}.{ext}"
    data = urllib.request.urlopen(url, timeout=30).read()
    with open(local, "wb") as fh:
        fh.write(data)
    return local


def _parse_bks(sol_path):
    """Read official BKS: (cost, n_routes) from a PyVRP .sol file."""
    cost, routes = None, 0
    with open(sol_path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            s = line.strip()
            if s.lower().startswith("route"):
                routes += 1
            elif s.lower().startswith("cost"):
                cost = float(s.split()[-1])
    return cost, routes


# --------------------------------------------------------------------------- #
# Solver
# --------------------------------------------------------------------------- #
def solve_vrptw(inst, time_limit_s=TIME_LIMIT_S):
    """Solve one VRPTW instance (vrplib dict) with OR-Tools.

    Returns (distance_float, n_vehicles_used, status_str) or (None, None, 'INF').
    """
    coords = [tuple(map(float, c)) for c in inst["node_coord"]]
    demands = [int(round(d)) for d in inst["demand"]]
    tw = [tuple(map(int, w)) for w in inst["time_window"]]
    capacity = int(inst["capacity"])
    service = int(inst.get("service_time", 0))
    n = len(coords)
    depot = 0
    max_vehicles = int(inst.get("vehicles", 25))

    # integer distance matrix (scaled)
    def d_scaled(i, j):
        return int(round(math.hypot(coords[i][0] - coords[j][0],
                                    coords[i][1] - coords[j][1]) * DIST_SCALE))

    horizon = max(w[1] for w in tw) + service + 1

    manager = pywrapcp.RoutingIndexManager(n, max_vehicles, depot)
    routing = pywrapcp.RoutingModel(manager)

    # arc cost = distance
    def dist_cb(a, b):
        return d_scaled(manager.IndexToNode(a), manager.IndexToNode(b))
    dist_idx = routing.RegisterTransitCallback(dist_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(dist_idx)

    # capacity
    def demand_cb(a):
        return demands[manager.IndexToNode(a)]
    dem_idx = routing.RegisterUnaryTransitCallback(demand_cb)
    routing.AddDimensionWithVehicleCapacity(
        dem_idx, 0, [capacity] * max_vehicles, True, "Capacity")

    # time: travel (scaled) + service; allow waiting via slack
    def time_cb(a, b):
        i, j = manager.IndexToNode(a), manager.IndexToNode(b)
        travel = math.hypot(coords[i][0] - coords[j][0],
                            coords[i][1] - coords[j][1])
        return int(round(travel)) + (service if i != depot else 0)
    time_idx = routing.RegisterTransitCallback(time_cb)
    routing.AddDimension(time_idx, horizon, horizon, False, "Time")
    time_dim = routing.GetDimensionOrDie("Time")
    for node in range(n):
        idx = manager.NodeToIndex(node)
        time_dim.CumulVar(idx).SetRange(tw[node][0], tw[node][1])
    # depot start time windows on each vehicle
    for v in range(max_vehicles):
        time_dim.CumulVar(routing.Start(v)).SetRange(tw[depot][0], tw[depot][1])

    # minimise vehicles first (large fixed cost), then distance
    routing.SetFixedCostOfAllVehicles(100000)

    params = pywrapcp.DefaultRoutingSearchParameters()
    # PARALLEL_CHEAPEST_INSERTION respects time windows while building the first
    # solution, so it stays feasible on tight-window R1/RC1 instances where
    # PATH_CHEAPEST_ARC fails to find any feasible starting point.
    params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION)
    params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    params.time_limit.FromSeconds(time_limit_s)

    sol = routing.SolveWithParameters(params)
    if sol is None:
        return None, None, "INF"

    total = 0
    used = 0
    for v in range(max_vehicles):
        idx = routing.Start(v)
        if not routing.IsEnd(sol.Value(routing.NextVar(idx))):
            used += 1
        while not routing.IsEnd(idx):
            nxt = sol.Value(routing.NextVar(idx))
            total += d_scaled(manager.IndexToNode(idx), manager.IndexToNode(nxt))
            idx = nxt
    return total / DIST_SCALE, used, "OK"


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    rows = []
    log = []

    def emit(line=""):
        print(line)
        log.append(line)

    emit("=" * 78)
    emit("OFFICIAL SOLOMON VRPTW BENCHMARK  (OR-Tools vs published BKS)")
    emit(f"source: {BASE_URL}")
    emit(f"instances: {len(ALL_INSTANCES)} (classic 100-customer set)")
    emit(f"solver: PATH_CHEAPEST_ARC + GUIDED_LOCAL_SEARCH, "
         f"{TIME_LIMIT_S}s/instance, dist scale x{DIST_SCALE}")
    emit("=" * 78)
    emit(f"{'instance':<9}{'BKS_dist':>10}{'BKS_veh':>8}"
         f"{'my_dist':>10}{'my_veh':>7}{'gap%':>8}{'status':>8}")
    emit("-" * 78)

    fam_gaps = {}
    for name in ALL_INSTANCES:
        try:
            vrp = _download(name, "vrp")
            sol = _download(name, "sol")
        except Exception as e:  # noqa: BLE001
            emit(f"{name:<9}  download failed: {repr(e)[:50]}")
            continue

        inst = vrplib.read_instance(vrp)
        bks_cost, bks_veh = _parse_bks(sol)
        my_dist, my_veh, status = solve_vrptw(inst)

        if status == "OK" and bks_cost:
            gap = (my_dist - bks_cost) / bks_cost * 100.0
            fam = next(f for f, g in FAMILIES.items() if name in g)
            fam_gaps.setdefault(fam, []).append(gap)
            emit(f"{name:<9}{bks_cost:>10.1f}{bks_veh:>8}"
                 f"{my_dist:>10.1f}{my_veh:>7}{gap:>8.1f}{status:>8}")
            rows.append({
                "instance": name, "bks_dist": bks_cost, "bks_vehicles": bks_veh,
                "my_dist": round(my_dist, 1), "my_vehicles": my_veh,
                "gap_pct": round(gap, 2), "status": status,
            })
        else:
            emit(f"{name:<9}{(bks_cost or 0):>10.1f}{bks_veh:>8}"
                 f"{'-':>10}{'-':>7}{'-':>8}{status:>8}")
            rows.append({
                "instance": name, "bks_dist": bks_cost, "bks_vehicles": bks_veh,
                "my_dist": None, "my_vehicles": None,
                "gap_pct": None, "status": status,
            })

    emit("-" * 78)
    emit("PER-FAMILY MEAN GAP TO BKS:")
    for fam in FAMILIES:
        if fam in fam_gaps and fam_gaps[fam]:
            gs = fam_gaps[fam]
            emit(f"  {fam:<4} n={len(gs):<3} mean gap = {sum(gs)/len(gs):>6.1f}%"
                 f"  (min {min(gs):.1f}%, max {max(gs):.1f}%)")
    all_gaps = [g for gs in fam_gaps.values() for g in gs]
    if all_gaps:
        emit("-" * 78)
        emit(f"OVERALL: solved {len(all_gaps)}/{len(ALL_INSTANCES)} instances, "
             f"mean gap to BKS = {sum(all_gaps)/len(all_gaps):.1f}%")
    emit("=" * 78)

    # write CSV
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["instance", "bks_dist", "bks_vehicles",
                                           "my_dist", "my_vehicles", "gap_pct",
                                           "status"])
        w.writeheader()
        w.writerows(rows)

    # write log
    with open(LOG_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(log) + "\n")

    print(f"\n[saved] {CSV_PATH}")
    print(f"[saved] {LOG_PATH}")
    print(f"[cached instances] {INSTANCE_DIR}")


if __name__ == "__main__":
    main()
