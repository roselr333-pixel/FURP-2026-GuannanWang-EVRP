"""
Week 1 baseline smoke test — Classical VRPTW with Google OR-Tools.

This is the FIRST concrete deliverable of the FURP EVRP project.
It solves a small Vehicle Routing Problem with Time Windows (VRPTW)
using OR-Tools, and records:
  - objective value (total distance)
  - feasibility status
  - runtime
  - textual route output

It runs TWO phases so you can already see the "baseline vs improvement"
story that the project asks for in Week 7:
  Phase A: greedy first solution (fast)
  Phase B: guided local search (better, uses a small time budget)

Later weeks will add battery / charging constraints to turn this into EVRP-TW.

Run:
  python src/experiments/week01_baseline.py
"""

import time
import os
import math
import importlib.metadata
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ORTOOLS_VERSION = importlib.metadata.version("ortools")

# ---------------------------------------------------------------------------
# 1. Small instance definition (6 nodes: depot 0 + 5 customers)
#    Distances are in arbitrary units (e.g. km * 10).
# ---------------------------------------------------------------------------
DEPOT = 0
NUM_VEHICLES = 2
VEHICLE_CAPACITY = 20

# Symmetric distance matrix (node 0 = depot)
DISTANCE = [
    [0, 10, 15, 20, 25, 30],
    [10, 0, 12, 18, 22, 28],
    [15, 12, 0, 10, 15, 20],
    [20, 18, 10, 0, 12, 16],
    [25, 22, 15, 12, 0, 10],
    [30, 28, 20, 16, 10, 0],
]

# Demand per node (depot = 0)
DEMAND = [0, 6, 8, 5, 7, 4]

# Time windows per node: (earliest, latest). Depot open 0..200.
TIME_WINDOWS = [
    (0, 200),   # depot
    (0, 100),   # customer 1
    (10, 120),  # customer 2
    (20, 140),  # customer 3
    (30, 160),  # customer 4
    (40, 180),  # customer 5
]

SERVICE_TIME = 10  # time spent serving each customer
SPEED = 1.0        # distance units per time unit


def build_model():
    manager = pywrapcp.RoutingIndexManager(len(DISTANCE), NUM_VEHICLES, DEPOT)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        f = manager.IndexToNode(from_index)
        t = manager.IndexToNode(to_index)
        return DISTANCE[f][t]

    transit_idx = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_idx)

    def demand_callback(from_index):
        return DEMAND[manager.IndexToNode(from_index)]

    demand_idx = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_idx, 0, [VEHICLE_CAPACITY] * NUM_VEHICLES, True, "Capacity"
    )

    def time_callback(from_index, to_index):
        f = manager.IndexToNode(from_index)
        t = manager.IndexToNode(to_index)
        return int(DISTANCE[f][t] / SPEED) + SERVICE_TIME

    time_idx = routing.RegisterTransitCallback(time_callback)
    routing.AddDimension(time_idx, 200, 200, False, "Time")
    time_dim = routing.GetDimensionOrDie("Time")
    for node in range(len(DISTANCE)):
        index = manager.NodeToIndex(node)
        tw = TIME_WINDOWS[node]
        time_dim.CumulVar(index).SetRange(tw[0], tw[1])
        routing.AddToAssignment(time_dim.SlackVar(index))
    for vehicle in range(NUM_VEHICLES):
        routing.AddVariableMinimizedByFinalizer(
            time_dim.CumulVar(routing.End(vehicle))
        )
    return manager, routing


def make_params(use_metaheuristic, time_budget_s):
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    if use_metaheuristic:
        params.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        params.time_limit.FromSeconds(time_budget_s)
    return params


def format_solution(manager, routing, solution):
    routes = []
    for vehicle in range(NUM_VEHICLES):
        index = routing.Start(vehicle)
        route = []
        while not routing.IsEnd(index):
            route.append(manager.IndexToNode(index))
            index = solution.Value(routing.NextVar(index))
        route.append(manager.IndexToNode(index))
        if len(route) > 2:
            routes.append((vehicle, route))
    return routes


def main():
    manager, routing = build_model()
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out_path = os.path.join(here, "src", "results", "week01_baseline_output.txt")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    lines = []
    lines.append("=" * 64)
    lines.append("WEEK 1 BASELINE SMOKE TEST — OR-Tools VRPTW")
    lines.append("=" * 64)
    lines.append(f"Instance: small VRPTW (1 depot + 5 customers, {NUM_VEHICLES} vehicles)")
    lines.append(f"Solver: OR-Tools {ORTOOLS_VERSION}")
    lines.append(f"OS: Windows | Python: 3.13 | Package manager: venv + pip")

    # ---- Phase A: greedy first solution ----
    t0 = time.perf_counter()
    sol_a = routing.SolveWithParameters(make_params(False, 0))
    t_a = time.perf_counter() - t0
    if sol_a is None:
        lines.append("STATUS: NO SOLUTION FOUND (infeasible)")
        lines.append(f"Phase A runtime: {t_a:.4f} s")
        text = "\n".join(lines)
        with open(out_path, "w") as fh:
            fh.write(text)
        print(text)
        return

    obj_a = sol_a.ObjectiveValue()
    routes_a = format_solution(manager, routing, sol_a)

    # ---- Phase B: guided local search ----
    t0 = time.perf_counter()
    sol_b = routing.SolveWithParameters(make_params(True, 3))
    t_b = time.perf_counter() - t0
    obj_b = sol_b.ObjectiveValue()
    routes_b = format_solution(manager, routing, sol_b)

    lines.append("STATUS: FEASIBLE")
    lines.append("-" * 64)
    lines.append("PHASE A — greedy first solution (PATH_CHEAPEST_ARC)")
    lines.append(f"  Objective (total distance): {obj_a}")
    lines.append(f"  Runtime: {t_a:.4f} s")
    for v, r in routes_a:
        lines.append(f"  Vehicle {v}: {r}")
    lines.append("-" * 64)
    lines.append("PHASE B — guided local search (3 s budget)")
    lines.append(f"  Objective (total distance): {obj_b}")
    lines.append(f"  Runtime: {t_b:.4f} s")
    for v, r in routes_b:
        lines.append(f"  Vehicle {v}: {r}")
    lines.append("-" * 64)
    improvement = obj_a - obj_b
    pct = (improvement / obj_a * 100) if obj_a else 0
    lines.append(f"Improvement from local search: {improvement} units ({pct:.1f}% shorter)")
    lines.append("Constraint check:")
    lines.append(f"  Capacity per vehicle <= {VEHICLE_CAPACITY}: enforced by solver")
    lines.append(f"  Time windows: enforced by solver")
    lines.append("=" * 64)

    text = "\n".join(lines)
    with open(out_path, "w") as fh:
        fh.write(text)
    print(text)
    print(f"\n[output saved to {out_path}]")

    # ---- route plot (Week 1 deliverable: one plot/route text) ----
    plot_path = os.path.join(os.path.dirname(out_path), "week01_routes.png")
    plot_routes(routes_b, plot_path)
    print(f"[route plot saved to {plot_path}]")


def plot_routes(routes, plot_path):
    """Circular-layout network plot (no coordinates available: distance matrix)."""
    n = len(DISTANCE)
    pos = {i: (math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n)) for i in range(n)}
    plt.figure(figsize=(6, 6))
    for i in range(n):
        color = "black" if i == DEPOT else "lightgray"
        plt.scatter([pos[i][0]], [pos[i][1]], c=color, s=200 if i == DEPOT else 90,
                    zorder=3)
        plt.text(pos[i][0], pos[i][1], str(i), ha="center", va="center",
                 color="white" if i == DEPOT else "black", fontsize=9, zorder=4)
    cmap = matplotlib.colormaps["tab10"]
    for k, (v, r) in enumerate(routes):
        for a, b in zip(r, r[1:]):
            x = [pos[a][0], pos[b][0]]
            y = [pos[a][1], pos[b][1]]
            plt.plot(x, y, "-", color=cmap(v % 10), linewidth=2, zorder=2)
    plt.title("Week 1 — VRPTW routes (depot=0, circle layout)")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(plot_path, dpi=110)
    plt.close()


if __name__ == "__main__":
    main()
