"""
Week 3 — Reproduce the baseline on a STANDARD benchmark instance.

Goal (per the 8-week roadmap, Week 3): "Reproduce one baseline — objective,
feasibility, runtime logs."

This script loads a small Solomon-format VRPTW instance
(`src/data/solomon_c101_small.txt`) and solves it with the same OR-Tools
classical VRPTW approach used in Week 1, so we have a *reproducible* baseline
on a standard instance format (not just a hand-made toy).

Run:
  python src/experiments/week03_reproduce.py
"""

import time
import os
import math
from ortools.constraint_solver import pywrapcp, routing_enums_pb2


def load_solomon(path):
    """Parse a minimal Solomon-format VRPTW file."""
    nodes = []
    n_vehicles = None
    capacity = None
    with open(path) as fh:
        lines = [ln.strip() for ln in fh if ln.strip()]
    i = 0
    while i < len(lines):
        if lines[i].startswith("NUMBER"):
            # next line: "3          200"
            parts = lines[i + 1].split()
            n_vehicles = int(parts[0])
            capacity = int(parts[1])
            i += 2
            continue
        if lines[i].startswith("CUST NO"):
            i += 1
            while i < len(lines) and not lines[i].startswith("CUST NO"):
                p = lines[i].split()
                if len(p) < 7:
                    break
                cid = int(p[0])
                x = float(p[1])
                y = float(p[2])
                demand = int(p[3])
                ready = int(p[4])
                due = int(p[5])
                service = int(p[6])
                nodes.append(
                    {
                        "id": cid,
                        "x": x,
                        "y": y,
                        "demand": demand,
                        "ready": ready,
                        "due": due,
                        "service": service,
                    }
                )
                i += 1
            break
        i += 1
    return nodes, n_vehicles, capacity


def build_distance(nodes):
    n = len(nodes)
    mat = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            d = math.hypot(nodes[i]["x"] - nodes[j]["x"], nodes[i]["y"] - nodes[j]["y"])
            mat[i][j] = int(round(d))
    return mat


def main():
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_path = os.path.join(here, "src", "data", "solomon_c101_small.txt")
    nodes, num_vehicles, vehicle_cap = load_solomon(data_path)
    dist = build_distance(nodes)
    n = len(nodes)
    depot = 0

    manager = pywrapcp.RoutingIndexManager(n, num_vehicles, depot)
    routing = pywrapcp.RoutingModel(manager)

    def dist_cb(from_idx, to_idx):
        return dist[manager.IndexToNode(from_idx)][manager.IndexToNode(to_idx)]

    transit = routing.RegisterTransitCallback(dist_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(transit)

    def demand_cb(from_idx):
        return nodes[manager.IndexToNode(from_idx)]["demand"]

    demand_idx = routing.RegisterUnaryTransitCallback(demand_cb)
    routing.AddDimensionWithVehicleCapacity(
        demand_idx, 0, [vehicle_cap] * num_vehicles, True, "Capacity"
    )

    def time_cb(from_idx, to_idx):
        return (
            dist[manager.IndexToNode(from_idx)][manager.IndexToNode(to_idx)]
            + nodes[manager.IndexToNode(from_idx)]["service"]
        )

    time_idx = routing.RegisterTransitCallback(time_cb)
    routing.AddDimension(time_idx, 1200, 1200, False, "Time")
    time_dim = routing.GetDimensionOrDie("Time")
    for node in range(n):
        index = manager.NodeToIndex(node)
        time_dim.CumulVar(index).SetRange(nodes[node]["ready"], nodes[node]["due"])
        routing.AddToAssignment(time_dim.SlackVar(index))

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    params.time_limit.FromSeconds(5)

    t0 = time.perf_counter()
    solution = routing.SolveWithParameters(params)
    elapsed = time.perf_counter() - t0

    out_path = os.path.join(here, "src", "results", "week03_reproduce_output.txt")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    lines = []
    lines.append("=" * 64)
    lines.append("WEEK 3 — BASELINE REPRODUCTION ON STANDARD INSTANCE")
    lines.append("=" * 64)
    lines.append(f"Instance: Solomon-format VRPTW (src/data/solomon_c101_small.txt)")
    lines.append(f"  nodes={n} (depot + {n-1} customers), vehicles={num_vehicles}, cap={vehicle_cap}")

    if solution is None:
        lines.append("STATUS: NO SOLUTION FOUND (infeasible)")
        lines.append(f"Runtime: {elapsed:.4f} s")
        text = "\n".join(lines)
        with open(out_path, "w") as fh:
            fh.write(text)
        print(text)
        return

    obj = solution.ObjectiveValue()
    lines.append("STATUS: FEASIBLE")
    lines.append(f"Objective (total distance): {obj}")
    lines.append(f"Runtime: {elapsed:.4f} s")
    lines.append("-" * 64)
    lines.append("ROUTES:")
    used = 0
    for v in range(num_vehicles):
        idx = routing.Start(v)
        route = []
        while not routing.IsEnd(idx):
            route.append(manager.IndexToNode(idx))
            idx = solution.Value(routing.NextVar(idx))
        route.append(manager.IndexToNode(idx))
        if len(route) > 2:
            used += 1
            load = sum(nodes[r]["demand"] for r in route[:-1])
            lines.append(f"  Vehicle {v}: {route}  (load={load})")
    lines.append(f"Vehicles used: {used} / {num_vehicles}")
    lines.append("=" * 64)
    text = "\n".join(lines)
    with open(out_path, "w") as fh:
        fh.write(text)
    print(text)
    print(f"\n[output saved to {out_path}]")


if __name__ == "__main__":
    main()
