"""
Week 4 — EVRP-TW: add battery capacity + charging stations.

Goal (Week 4): "EVRP-TW constraints — metric table with time and battery
violations."

We extend the classical VRPTW with an electric-vehicle battery constraint.
Following the OR-Tools fuel/recharge pattern:
  * cumul variable tracks ENERGY USED (starts at 0 = full battery);
  * travelling an arc adds energy consumed (positive);
  * at CHARGING STATIONS the used-energy is allowed to reset (recharge);
  * the used-energy must never exceed battery capacity (=> battery violation).

We report, for several battery capacities, feasibility and number of recharges.
This is the "battery violation table" the project asks for.

Run:
  python src/experiments/week04_evrp_tw.py
"""

import time
import os
import math
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

# ---- small instance (coordinates; Euclidean distances) ----
# Corridor layout to clearly show charging matters:
#   depot(0) -- C1(25) -- STATION(50) -- C2(75) -- C3(100)   (all on x-axis)
# A medium battery cannot reach C3 directly, but recharging at the station
# (node 2) makes the instance feasible.
COORDS = {
    0: (0, 0),     # depot / charging station
    1: (25, 0),    # customer C1
    2: (50, 0),    # charging station S
    3: (75, 0),    # customer C2
    4: (100, 0),   # customer C3 (too far for a small battery)
}
DEMAND = [0, 10, 0, 10, 10]   # station node has no demand
CHARGING_STATIONS = {0, 2}
CONSUMPTION = 1.0          # energy units per distance unit
SERVICE_TIME = 10
TIME_HORIZON = 10000
NUM_VEHICLES = 3
VEHICLE_CAPACITY = 100


def dist(a, b):
    return int(round(math.hypot(COORDS[a][0] - COORDS[b][0], COORDS[a][1] - COORDS[b][1])))


def make_params(routing):
    p = pywrapcp.DefaultRoutingSearchParameters()
    p.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    p.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    p.time_limit.FromSeconds(5)
    return p


def build_model(battery_capacity, allow_recharge):
    n = len(COORDS)
    manager = pywrapcp.RoutingIndexManager(n, NUM_VEHICLES, 0)
    routing = pywrapcp.RoutingModel(manager)

    def dist_cb(f, t):
        return dist(manager.IndexToNode(f), manager.IndexToNode(t))

    transit = routing.RegisterTransitCallback(dist_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(transit)

    def dem_cb(f):
        return DEMAND[manager.IndexToNode(f)]

    dem_idx = routing.RegisterUnaryTransitCallback(dem_cb)
    routing.AddDimensionWithVehicleCapacity(
        dem_idx, 0, [VEHICLE_CAPACITY] * NUM_VEHICLES, True, "Capacity"
    )

    def time_cb(f, t):
        return dist(manager.IndexToNode(f), manager.IndexToNode(t)) + SERVICE_TIME

    time_idx = routing.RegisterTransitCallback(time_cb)
    routing.AddDimension(time_idx, TIME_HORIZON, TIME_HORIZON, False, "Time")
    time_dim = routing.GetDimensionOrDie("Time")
    for node in range(n):
        idx = manager.NodeToIndex(node)
        time_dim.CumulVar(idx).SetRange(0, TIME_HORIZON)

    # battery: cumul = ENERGY USED (0 = full battery).
    # Travelling an arc adds energy consumed (positive).
    # Arriving AT a charging station recharges to full -> negative transit.
    def battery_cb(f, t):
        fn = manager.IndexToNode(f)
        tn = manager.IndexToNode(t)
        if allow_recharge and tn in CHARGING_STATIONS:
            return -battery_capacity  # recharge to full on arrival
        return int(round(dist(fn, tn) * CONSUMPTION))

    batt_idx = routing.RegisterTransitCallback(battery_cb)
    # slack_max = battery_capacity so a recharge (negative transit into a
    # station) can be represented without violating the slack >= 0 rule.
    routing.AddDimension(batt_idx, battery_capacity, battery_capacity, False, "Battery")
    batt_dim = routing.GetDimensionOrDie("Battery")
    for v in range(NUM_VEHICLES):
        batt_dim.CumulVar(routing.Start(v)).SetValue(0)
    for node in range(n):
        idx = manager.NodeToIndex(node)
        batt_dim.CumulVar(idx).SetRange(0, battery_capacity)

    return manager, routing, batt_dim


def count_recharges(manager, routing, solution, batt_dim):
    recharges = 0
    for v in range(NUM_VEHICLES):
        idx = routing.Start(v)
        prev = None
        while not routing.IsEnd(idx):
            node = manager.IndexToNode(idx)
            if prev is not None and node in CHARGING_STATIONS:
                arr = solution.Value(batt_dim.CumulVar(prev)) + int(
                    round(dist(manager.IndexToNode(prev), node) * CONSUMPTION)
                )
                now = solution.Value(batt_dim.CumulVar(idx))
                if now == 0 and arr > 0:
                    recharges += 1
            prev = idx
            idx = solution.Value(routing.NextVar(idx))
    return recharges


def solve(battery_capacity, allow_recharge):
    manager, routing, batt_dim = build_model(battery_capacity, allow_recharge)
    params = make_params(routing)
    t0 = time.perf_counter()
    sol = routing.SolveWithParameters(params)
    elapsed = time.perf_counter() - t0
    if sol is None:
        return False, elapsed, 0
    recharges = count_recharges(manager, routing, sol, batt_dim)
    return True, elapsed, recharges


def main():
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out_path = os.path.join(here, "src", "results", "week04_evrp_tw_output.txt")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    lines = []
    lines.append("=" * 64)
    lines.append("WEEK 4 — EVRP-TW (battery + charging stations)")
    lines.append("=" * 64)
    lines.append(f"Instance: 6 nodes (depot + 5 customers), charging stations = {sorted(CHARGING_STATIONS)}")
    lines.append(f"Energy consumption = {CONSUMPTION} per distance unit")
    lines.append("")
    lines.append("BATTERY VIOLATION TABLE (recharge allowed at stations)")
    lines.append(f"{'Battery cap':>12} | {'Feasible':>9} | {'Recharges':>10} | {'Runtime(s)':>10}")
    lines.append("-" * 50)
    for cap in [100, 150, 200, 250]:
        feasible, elapsed, recharges = solve(cap, allow_recharge=True)
        lines.append(f"{cap:>12} | {str(feasible):>9} | {recharges:>10} | {elapsed:>10.3f}")

    lines.append("")
    lines.append("Comparison — NO recharge allowed (pure EV):")
    for cap in [100, 150, 200, 250]:
        feasible, elapsed, recharges = solve(cap, allow_recharge=False)
        lines.append(f"  battery={cap}: feasible={feasible}, runtime={elapsed:.3f}s")

    text = "\n".join(lines)
    with open(out_path, "w") as fh:
        fh.write(text)
    print(text)
    print(f"\n[output saved to {out_path}]")


if __name__ == "__main__":
    main()
