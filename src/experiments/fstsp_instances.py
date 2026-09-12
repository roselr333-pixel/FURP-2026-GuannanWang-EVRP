"""
Standard (Solomon-derived) instances for the truck-drone experiments.

The W8 notes list "instances are random-geometry synthetic ones" as a limitation.
This module replaces the random geometry with the coordinates of the official
Solomon instances already in the repo (src/instances/official_solomon/*.vrp),
so the spatial pattern is the real clustered (C) / uniform (R) / mixed (RC)
topology instead of a random ring.

Reusing the paper convention: a FSTSP instance is a Solomon instance with the
first n customers kept and a drone added. To keep the drone-range regime
comparable to the earlier synthetic runs (where the drone range R_D = 160 was
tuned against a customer cloud of a certain radius), the Solomon coordinates are
translated so the depot is at the origin and uniformly scaled so that the
customers' RMS radius equals that of the synthetic generator at the same n.
Only the topology changes; the model constants (truck/drone speed, service time,
endurance R_D) stay the same.

Run (self-test):
  python src/experiments/fstsp_instances.py
"""

import os
import math
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import week06_ground_air_evrp_tw as w6

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(_HERE))
SOLOMON_DIR = os.path.join(REPO, "src", "instances", "official_solomon")


def parse_solomon(path):
    """Parse a TSPLIB-style Solomon VRPTW .vrp file. Returns (coords, demands),
    both dicts keyed by 1-based node id (node 1 is the depot)."""
    coords, demands = {}, {}
    section = None
    with open(path) as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if line.endswith("SECTION"):
                section = line
                continue
            if line == "EOF":
                break
            if section == "NODE_COORD_SECTION":
                p = line.split()
                coords[int(p[0])] = (float(p[1]), float(p[2]))
            elif section == "DEMAND_SECTION":
                p = line.split()
                demands[int(p[0])] = float(p[1])
            elif section == "DEPOT_SECTION":
                # first entry is the depot id, then -1
                p = line.split()
                if p and p[0] != "-1":
                    pass
    return coords, demands


def _synthetic_rms(n):
    """RMS radius of the synthetic generator: r ~ U[15, 30 + 4n]."""
    a, b = 15.0, 30.0 + 4.0 * n
    return math.sqrt((a * a + a * b + b * b) / 3.0)


def make_solomon_fstsp(name, n, start=0):
    """Build a FSTSP instance from Solomon instance `name` (e.g. 'C101') using
    `n` of its customers beginning at `start` (default: the first n, which is
    the paper convention). Coordinates are translated (depot -> origin) and
    scaled so the customer RMS radius matches the synthetic generator at n.

    `start` exists because the Solomon files in this repo share coordinates
    within a family prefix, so "the first n customers" gives only one point set
    per family; sliding the window produces genuinely different customer sets
    from the same official topology."""
    coords, demands = parse_solomon(os.path.join(SOLOMON_DIR, name + ".vrp"))
    depot_xy = coords[1]
    all_nodes = [i for i in range(2, len(coords) + 1)]
    cust_nodes = all_nodes[start:start + n]
    if len(cust_nodes) < n:
        raise ValueError(
            f"{name} has only {len(all_nodes)} customers; "
            f"asked for n={n} starting at {start}")

    # translate depot to origin and measure the current RMS radius
    raw = {i: (coords[i][0] - depot_xy[0], coords[i][1] - depot_xy[1])
           for i in cust_nodes}
    rms0 = math.sqrt(sum(x * x + y * y for x, y in raw.values()) / n)
    scale = _synthetic_rms(n) / rms0 if rms0 > 0 else 1.0

    customers = {k + 1: (xy[0] * scale, xy[1] * scale)
                 for k, xy in enumerate(raw.values())}
    depot = (0.0, 0.0)
    coord = {0: depot}
    coord.update(customers)
    demand = {k + 1: demands[node] for k, node in enumerate(cust_nodes)}
    tw = {cid: (0.0, 1e9) for cid in customers}   # FSTSP evaluator ignores TW
    return {
        "depot": depot, "customers": customers, "stations": {},
        "tw": tw, "demand": demand, "coord": coord,
        "Q": w6.Q_DEFAULT, "n": n,
        "source": f"Solomon {name} (customers {start + 1}-{start + n})",
    }


# The Solomon files in this repo share coordinates within a family prefix
# (C1xx / C2xx / R1xx=R2xx / RC1xx=RC2xx), so these four are the distinct
# spatial topologies: clustered, clustered-2, uniform, mixed.
FAMILIES = ["C101", "C201", "R101", "RC101"]


def main():
    for name in FAMILIES:
        for n in [10, 20, 30, 50]:
            inst = make_solomon_fstsp(name, n)
            xs = [c[0] for c in inst["customers"].values()]
            ys = [c[1] for c in inst["customers"].values()]
            rms = math.sqrt(sum(x * x + y * y
                                for x, y in inst["customers"].values()) / n)
            print(f"{name} n={n:3d}: x[{min(xs):7.1f},{max(xs):7.1f}] "
                  f"y[{min(ys):7.1f},{max(ys):7.1f}] RMS={rms:6.1f} "
                  f"(target {_synthetic_rms(n):6.1f})")


if __name__ == "__main__":
    main()
