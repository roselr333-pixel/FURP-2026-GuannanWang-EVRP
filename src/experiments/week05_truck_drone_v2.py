"""
Week 5 (v2) — Truck + Drone with LAUNCH/LAND at ANY node (FSTSP-style).

The first truck-drone script (week05_truck_drone.py) only let the drone fly a
single loop from the depot and back. That is the limitation the checkpoint
listed: "drone launched/recovered at depot (no mid-route rendezvous yet)".

This v2 removes that limitation with a greedy insertion heuristic in the
spirit of the Flying Sidekick TSP (Murray & Chu, 2015):

  * The truck runs a route visiting a subset of customers.
  * The drone is CARRIED by the truck and can be LAUNCHED at any truck node i
    to serve one customer k, then RECOVERED at any later truck node j.
  * A drone trip (i -> k -> j) is feasible only if:
      (a) RANGE:  dist(i,k) + dist(k,j) <= DRONE_RANGE
      (b) RENDEZVOUS: the drone must land at j no later than the truck arrives
          at j  (drone may wait at j, but cannot land after the truck left)
  * We greedily offload the customer that gives the biggest truck-distance
    saving, repeat until no beneficial/feasible trip remains.

Makespan = max(truck completion time, drone completion time). The drone can
fly several trips in sequence (it waits on the truck between recoveries).

Run:
  python src/experiments/week05_truck_drone_v2.py
"""

import os
import math
from collections import defaultdict

# same instance as week05 (so the comparison is fair)
DEPOT = (0, 0)
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
DRONE_RANGE = 150.0  # max drone flight length i->k->j


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def coord(node):
    """Coordinate of a route node; node 0 is the depot."""
    return DEPOT if node == 0 else CUSTOMERS[node]


# ---------------------------------------------------------------------------
# baseline helpers (truck-only, and the old depot-only drone model)
# ---------------------------------------------------------------------------
def nn_tour(points):
    remaining = list(points)
    route = []
    cur = DEPOT
    while remaining:
        nxt = min(remaining, key=lambda p: dist(cur, points[p]))
        route.append(nxt)
        cur = points[nxt]
        remaining.remove(nxt)
    return route


def truck_makespan(route):
    """route = list of customer ids (no depot). Returns (makespan, travel)."""
    if not route:
        return 0.0, 0.0
    travel = dist(DEPOT, CUSTOMERS[route[0]])
    for a, b in zip(route, route[1:]):
        travel += dist(CUSTOMERS[a], CUSTOMERS[b])
    travel += dist(CUSTOMERS[route[-1]], DEPOT)
    return travel / TRUCK_SPEED + len(route) * SERVICE_TIME, travel


def depot_only_drone():
    """Re-implements the OLD model: drone = one depot loop, truck = other loop."""
    order = sorted(CUSTOMERS, key=lambda c: -dist(DEPOT, CUSTOMERS[c]))
    drone_set = set(order[: len(order) // 2])
    truck_set = set(order[len(order) // 2:])
    d_mk, _ = truck_makespan(list(drone_set))
    t_mk, _ = truck_makespan(list(truck_set))
    return max(d_mk, t_mk), drone_set, truck_set


# ---------------------------------------------------------------------------
# v2: flexible launch/land heuristic
# ---------------------------------------------------------------------------
def simulate(route, drone_trips):
    """Compute truck arrival times at each route position, and drone makespan.

    route: list of customer ids (truck visits, no depot bookends).
    drone_trips: list of (launch_node, k, recover_node) -- node ids, NOT
                 positions, so they stay valid after the truck route shrinks.
    """
    full = [0] + route + [0]  # 0 = depot (start and end)
    arr = [0.0] * len(full)
    for p in range(1, len(full)):
        prev = full[p - 1]
        cur = full[p]
        d = dist(coord(prev), coord(cur))
        arr[p] = arr[p - 1] + d / TRUCK_SPEED + (SERVICE_TIME if cur != 0 else 0)

    drone_free = 0.0
    for ln, k, rn in drone_trips:
        i_pos = 0 if ln == 0 else full.index(ln)
        j_pos = (len(full) - 1) if rn == 0 else full.index(rn)
        launch = arr[i_pos]
        trip = (dist(coord(ln), coord(k)) +
                dist(coord(k), coord(rn))) / DRONE_SPEED + SERVICE_TIME
        landing = launch + trip
        drone_free = max(drone_free, landing)
    return arr, drone_free


def flexible_drone():
    route = nn_tour(CUSTOMERS)          # truck initially serves everyone
    drone_trips = []
    while True:
        best = None  # (saving, k, i_pos, j_pos)
        full = [0] + route + [0]
        arr, _ = simulate(route, drone_trips)
        # nodes already used as a launch/recover point must stay on the truck
        # route, so they can no longer be offloaded to the drone.
        used_endpoints = {n for (ln, _, rn) in drone_trips for n in (ln, rn)}
        # distance of a sub-path through a list of nodes
        def seg_dist(nodes):
            s = 0.0
            for a, b in zip(nodes, nodes[1:]):
                s += dist(DEPOT, CUSTOMERS[b]) if a == 0 else (
                    dist(CUSTOMERS[a], DEPOT) if b == 0 else dist(CUSTOMERS[a], CUSTOMERS[b]))
            return s

        inner = route  # positions 1..len(route) in `full` map to route indices
        for pk in range(len(route)):
            k = route[pk]
            if k in used_endpoints:
                continue
            for i_pos in range(0, pk + 1):          # launch before/at k
                for j_pos in range(pk + 2, len(full)):  # recover after k
                    # original sub-path i_pos..j_pos (includes k)
                    orig = full[i_pos:j_pos + 1]
                    # new sub-path with k removed
                    new_nodes = [n for n in orig if n != k]
                    save = seg_dist(orig) - seg_dist(new_nodes)
                    if save <= 0:
                        continue
                    # feasibility
                    di = dist(coord(full[i_pos]), coord(k))
                    dj = dist(coord(k), coord(full[j_pos]))
                    if di + dj > DRONE_RANGE:
                        continue
                    truck_ij = arr[j_pos] - arr[i_pos]
                    drone_trip = (di + dj) / DRONE_SPEED + SERVICE_TIME
                    if drone_trip > truck_ij:  # would land after truck left
                        continue
                    if best is None or save > best[0]:
                        best = (save, k, i_pos, j_pos)
        if best is None:
            break
        _, k, i_pos, j_pos = best
        route.remove(k)
        drone_trips.append((full[i_pos], k, full[j_pos]))  # store node ids

    arr, drone_free = simulate(route, drone_trips)
    truck_mk, truck_travel = truck_makespan(route)
    collab = max(truck_mk, drone_free)
    return collab, route, drone_trips, truck_travel, drone_free


def main():
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out_path = os.path.join(here, "src", "results", "week05_truck_drone_v2_output.txt")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # baselines
    truck_mk, truck_travel = truck_makespan(list(CUSTOMERS.keys()))
    depot_mk, drone_set, truck_set = depot_only_drone()

    # v2
    collab, route, trips, t_travel, d_free = flexible_drone()

    L = []
    L.append("=" * 70)
    L.append("WEEK 5 (v2) TRUCK + DRONE — flexible launch/land (FSTSP-style)")
    L.append("=" * 70)
    L.append(f"Customers: {len(CUSTOMERS)} | truck speed={TRUCK_SPEED}, "
             f"drone speed={DRONE_SPEED}, drone range={DRONE_RANGE}")
    L.append("")
    L.append(f"TRUCK-ONLY makespan        : {truck_mk:.1f}")
    L.append(f"DEPOT-ONLY DRONE (old)     : {depot_mk:.1f}   "
             f"(drone loop {sorted(drone_set)} | truck loop {sorted(truck_set)})")
    L.append("")
    L.append(f"V2 FLEXIBLE DRONE makespan : {collab:.1f}")
    L.append(f"  truck serves {sorted(route)} (travel={t_travel:.1f})")
    L.append(f"  drone makespan (last landing) = {d_free:.1f}")
    L.append(f"  drone trips (launch node -> customer -> recover node):")
    for (ln, k, rn) in trips:
        L.append(f"    node {ln} -> customer {k} -> node {rn}")
    L.append("")
    imp_vs_truck = (truck_mk - collab) / truck_mk * 100
    imp_vs_depot = (depot_mk - collab) / depot_mk * 100
    L.append(f"Improvement vs truck-only      : {imp_vs_truck:.1f}%")
    L.append(f"Improvement vs depot-only drone: {imp_vs_depot:.1f}% "
             f"(shows the limitation is removed)")
    L.append("")
    L.append("What changed vs the old model:")
    L.append("  - drone is no longer confined to a depot loop;")
    L.append("  - it is carried by the truck and launched/recovered at any node;")
    L.append("  - each trip must satisfy RANGE and RENDEZVOUS (land by truck ETA);")
    L.append("  - greedy insertion keeps the truck route feasible and short.")
    L.append("=" * 70)

    text = "\n".join(L)
    with open(out_path, "w") as f:
        f.write(text)
    print(text)
    print(f"\n[output saved to {out_path}]")


if __name__ == "__main__":
    main()
