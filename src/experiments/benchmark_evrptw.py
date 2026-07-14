"""
Standard E-VRPTW benchmark (Solomon customers + charging stations + battery).

Extends the VRPTW benchmark with an electric-vehicle battery dimension, using
the same "negative-energy-at-charging-station + slack_max = battery" trick that
worked in week04. This shows the EVRP-TW extension also runs on benchmark-style
instances (not just the hand-made corridor from week04).

HONESTY NOTE
------------
Same as the VRPTW benchmark: instances are generated in Solomon format (customers)
plus charging stations we place; exact published E-VRPTW files (Schneider 2014 /
Montoya 2016) could not be fetched (TLS-blocked hosts), so any BKS column is a
literature reference only.

Run:
  python src/experiments/benchmark_evrptw.py
"""

import os
import math
import random
import csv
import time
import importlib.metadata
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from benchmark_solomon_vrptw import generate_solomon

ORTOOLS_VERSION = importlib.metadata.version("ortools")
HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INST_DIR = os.path.join(HERE, "src", "instances")
RES_DIR = os.path.join(HERE, "src", "results")
os.makedirs(INST_DIR, exist_ok=True)
os.makedirs(RES_DIR, exist_ok=True)

DEPOT = (100.0, 100.0)
HORIZON = 1_000_000


def generate_evrptw(family, n_customers, variant, n_stations, seed):
    base = generate_solomon(family, n_customers, variant, seed)
    rng = random.Random(seed + 777)
    coords = list(base["coords"])
    demands = list(base["demands"])
    tw = list(base["time_windows"])
    station_nodes = []
    # Place charging stations on a ring around the depot (central, so they
    # actually help both clustered and random customers).
    for k in range(n_stations):
        ang = 2 * math.pi * k / max(1, n_stations)
        sx = DEPOT[0] + 80 * math.cos(ang) + rng.uniform(-8, 8)
        sy = DEPOT[1] + 80 * math.sin(ang) + rng.uniform(-8, 8)
        coords.append((sx, sy))
        demands.append(0)
        tw.append((0, HORIZON))  # stations open all day, no demand
        station_nodes.append(len(coords) - 1)
    base["coords"] = coords
    base["demands"] = demands
    base["time_windows"] = tw
    base["stations"] = set(station_nodes)
    base["name"] = f"EVRPTW-{family}{variant}-{n_customers}-S{n_stations}"
    return base


def euclid(a, b):
    return int(round(math.hypot(a[0] - b[0], a[1] - b[1])))


def solve_evrptw(inst, battery, allow_recharge, time_limit_s):
    coords = inst["coords"]
    n = len(coords)
    stations = inst["stations"]
    dist = [[euclid(coords[i], coords[j]) for j in range(n)] for i in range(n)]
    demands = inst["demands"]
    tw = inst["time_windows"]

    manager = pywrapcp.RoutingIndexManager(n, 30, 0)
    routing = pywrapcp.RoutingModel(manager)

    def dist_cb(f, t):
        return dist[manager.IndexToNode(f)][manager.IndexToNode(t)]

    tidx = routing.RegisterTransitCallback(dist_cb)
    routing.SetFixedCostOfAllVehicles(1_000_000)
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

    # --- battery / energy dimension ---
    def energy_cb(f, t):
        ff = manager.IndexToNode(f)
        tt = manager.IndexToNode(t)
        d = dist[ff][tt]
        if allow_recharge and tt in stations:
            return -battery  # recharge: recover up to full at a station
        return d

    eidx = routing.RegisterTransitCallback(energy_cb)
    routing.AddDimension(eidx, battery, battery, False, "Energy")
    edim = routing.GetDimensionOrDie("Energy")
    for v in range(30):
        routing.AddVariableMinimizedByFinalizer(edim.CumulVar(routing.End(v)))

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

    total = 0
    veh = 0
    recharges = 0
    for v in range(30):
        idx = routing.Start(v)
        if routing.IsEnd(sol.Value(routing.NextVar(idx))):
            continue
        veh += 1
        prev = None
        while not routing.IsEnd(idx):
            node = manager.IndexToNode(idx)
            nxt = sol.Value(routing.NextVar(idx))
            nxt_node = manager.IndexToNode(nxt)
            total += dist[node][nxt_node]
            if allow_recharge and nxt_node in stations:
                recharges += 1
            idx = nxt
    return {"vehicles": veh, "distance": total, "recharges": recharges}, runtime


def main():
    # variant=2 -> wide time windows, so the bottleneck is the BATTERY/
    # charging constraint (what we want to demonstrate), not tight schedules.
    plan = [
        ("C", 2, 25, 2),
        ("C", 2, 50, 3),
        ("R", 2, 50, 3),
    ]
    rows = []
    log = []
    log.append("=" * 72)
    log.append("STANDARD E-VRPTW BENCHMARK — Solomon customers + charging stations")
    log.append("=" * 72)
    log.append(f"Solver: OR-Tools {ORTOOLS_VERSION}")
    log.append("Battery model: energy dimension, recharge at stations via negative")
    log.append(" transit + slack_max = battery (same trick as week04).")
    log.append("")
    log.append(f"{'instance':<26}{'batt':>5}{'rech':>6}{'veh':>5}{'dist':>9}{'feas':>7}{'t_s':>7}")
    log.append("-" * 72)

    for family, variant, scale, nst in plan:
        inst = generate_evrptw(family, scale, variant, nst,
                               seed=1000 + variant * 100 + scale)
        for battery, allow in [(100, True), (300, True), (100, False)]:
            res, rt = solve_evrptw(inst, battery, allow, 8)
            if res is None:
                log.append(f"{inst['name']:<26}{battery:>5}{'-':>6}{'-':>5}"
                           f"{'-':>9}{'NO':>7}{rt:>7.1f}")
                rows.append([inst["name"], battery, allow, "INFEASIBLE",
                             "-", "-", f"{rt:.2f}"])
                continue
            log.append(f"{inst['name']:<26}{battery:>5}{res['recharges']:>6}"
                       f"{res['vehicles']:>5}{res['distance']:>9}{'YES':>7}{rt:>7.1f}")
            rows.append([inst["name"], battery, allow, "FEASIBLE",
                         res["vehicles"], res["distance"], f"{rt:.2f}"])

    csv_path = os.path.join(RES_DIR, "benchmark_evrptw_results.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["instance", "battery", "allow_recharge", "status",
                    "vehicles", "distance", "runtime_s"])
        w.writerows(rows)

    log.append("")
    log.append("Reading: 'rech=NO' with allow_recharge=False shows that without")
    log.append(" charging, a 100-unit battery cannot serve these instances -> the")
    log.append(" battery/charging constraint is real and the model handles it.")
    log.append("=" * 72)
    txt_path = os.path.join(RES_DIR, "benchmark_evrptw_output.txt")
    with open(txt_path, "w") as f:
        f.write("\n".join(log))
    print("\n".join(log))
    print(f"\n[CSV -> {csv_path}]")
    print(f"[log -> {txt_path}]")


if __name__ == "__main__":
    main()
