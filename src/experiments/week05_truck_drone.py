"""
Week 5 — Ground-Air collaborative routing (truck + drone).

Goal (Week 5): "truck-drone formulation — synchronization and constraint note"
and report "makespan for truck-drone collaboration".

This is a SIMPLIFIED HEURISTIC BASELINE (the project explicitly allows
"small custom instances plus heuristic baseline" for the truck-drone track):

  * One truck and one drone both start at the depot at t = 0 (synchronization).
  * Each customer is assigned to either the truck or the drone.
  * The truck runs a nearest-neighbour loop; the drone runs a nearest-neighbour
    loop (drone is faster: speed > truck speed).
  * Makespan = max(truck completion time, drone completion time) — they operate
    in parallel and must both finish (return to depot) before the job is done.

We compare truck-ONLY vs truck+drone makespan to show the collaboration benefit.

Run:
  python src/experiments/week05_truck_drone.py
"""

import os
import math
from collections import defaultdict

# instance: depot + customers (coordinates, Euclidean distances)
DEPOSIT = (0, 0)
CUSTOMERS = {
    1: (30, 40),
    2: (60, 20),
    3: (80, 70),
    4: (20, 80),
    5: (90, 10),
    6: (50, 90),
}
TRUCK_SPEED = 1.0
DRONE_SPEED = 2.0
SERVICE_TIME = 10


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def nearest_neighbour_tour(points):
    """Return (route, travel_distance) starting/ending at depot (points excludes depot)."""
    remaining = list(points)
    route = []
    cur = DEPOSIT
    total = 0.0
    while remaining:
        nxt = min(remaining, key=lambda p: dist(cur, points[p]))
        total += dist(cur, points[nxt])
        route.append(nxt)
        cur = points[nxt]
        remaining.remove(nxt)
    total += dist(cur, DEPOSIT)  # return to depot
    return route, total


def makespan(points, speed):
    _, travel = nearest_neighbour_tour(points)
    n = len(points)
    return travel / speed + n * SERVICE_TIME


def main():
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out_path = os.path.join(here, "src", "results", "week05_truck_drone_output.txt")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    lines = []
    lines.append("=" * 64)
    lines.append("WEEK 5 — TRUCK + DRONE COLLABORATIVE ROUTING (heuristic)")
    lines.append("=" * 64)
    lines.append(f"Customers: {len(CUSTOMERS)} | truck speed={TRUCK_SPEED}, drone speed={DRONE_SPEED}")
    lines.append("Synchronization: both start at depot at t=0; operate in parallel.")
    lines.append("")

    # truck-only baseline
    truck_route, truck_travel = nearest_neighbour_tour(CUSTOMERS)
    truck_mk = makespan(CUSTOMERS, TRUCK_SPEED)
    lines.append("TRUCK-ONLY:")
    lines.append(f"  route (depot -> {' -> '.join(map(str, truck_route))} -> depot)")
    lines.append(f"  travel distance = {truck_travel:.1f}")
    lines.append(f"  makespan = {truck_mk:.1f}")
    lines.append("")

    # assign customers to drone vs truck: drone takes the farthest-from-depot
    # customers (it is faster and good for long legs).
    order = sorted(CUSTOMERS, key=lambda c: -dist(DEPOSIT, CUSTOMERS[c]))
    drone_set = set(order[: len(order) // 2])
    truck_set = set(order[len(order) // 2:])
    drone_pts = {c: CUSTOMERS[c] for c in drone_set}
    truck_pts = {c: CUSTOMERS[c] for c in truck_set}

    d_route, d_travel = nearest_neighbour_tour(drone_pts)
    t_route, t_travel = nearest_neighbour_tour(truck_pts)
    drone_mk = makespan(drone_pts, DRONE_SPEED)
    truck_mk2 = makespan(truck_pts, TRUCK_SPEED)
    collab_mk = max(drone_mk, truck_mk2)

    lines.append("TRUCK + DRONE (parallel):")
    lines.append(f"  drone serves {sorted(drone_set)}: route (depot -> {' -> '.join(map(str, d_route))} -> depot), travel={d_travel:.1f}")
    lines.append(f"  truck serves {sorted(truck_set)}: route (depot -> {' -> '.join(map(str, t_route))} -> depot), travel={t_travel:.1f}")
    lines.append(f"  drone makespan = {drone_mk:.1f}")
    lines.append(f"  truck makespan = {truck_mk2:.1f}")
    lines.append(f"  COLLABORATION MAKESPAN = max = {collab_mk:.1f}")
    lines.append("")
    improvement = (truck_mk - collab_mk) / truck_mk * 100
    lines.append(f"Improvement vs truck-only: {improvement:.1f}% shorter makespan")
    lines.append("")
    lines.append("Constraint notes (simplified baseline):")
    lines.append("  - drone launched/recovered at depot (no mid-route rendezvous yet);")
    lines.append("  - synchronization = both depart depot at t=0;")
    lines.append("  - energy/service-time for drone and truck not yet modelled (Week 4 battery")
    lines.append("    idea can be extended to the truck; drone battery is future work).")

    text = "\n".join(lines)
    with open(out_path, "w") as fh:
        fh.write(text)
    print(text)
    print(f"\n[output saved to {out_path}]")


if __name__ == "__main__":
    main()
