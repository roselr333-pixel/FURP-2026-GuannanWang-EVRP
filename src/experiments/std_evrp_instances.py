"""
Standard-instance adapter for the ground-air EVRP-TW model.

The week-6 synthetic generator scatters customers on a random ring around the
depot. To test whether those conclusions generalise, this module turns the
**original Schneider (2014) E-VRPTW instances** (real coordinates, real time
windows, real charging stations, the paper's own battery parameters) into the
instance dictionary `week06_ground_air_evrp_tw` expects, so the same V0/V1/V2
pipeline can be re-run on standard data.

Mapping (per `instances/schneider_evrptw/readme.txt`):

| model field | source | note |
|---|---|---|
| coordinates | the file | km |
| time unit | minutes | the paper sets `v = 1`, so travel time == distance and the model's `V_T = 1` is exact |
| time windows | ready / due | minutes, as given (waiting allowed) |
| service | `ServiceTime` | 90 min in these instances (the synthetic default is 10) |
| battery `Q` | `Q / r` | tank / consumption rate = range in distance units |
| recharge | `Q * g` | full charge from empty; the model always refills to full |
| capacity `cap` | `C` | the paper's load capacity, now enforced by the model |
| drone range | `DRONE_RANGE_FACTOR` x mean depot-customer distance | keeps the drone's reach comparable to the synthetic setting, where `R_D = 160` is 2.6-3.4x that distance; stored as `inst["drone_range"]` |

A note on the fleet: Schneider's model uses several vehicles (`m` in the file)
while the W6 line uses **one** truck, so `cap_mode="file"` (the paper's `C`)
can only be satisfied for small customer subsets; `cap_mode="model"` uses the W6
default `CAP = 1000` so the geometry effect can be read separately from the
fleet-size mismatch.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schneider_evrptw as SE
import week06_ground_air_evrp_tw as w6

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INST_DIR = os.path.join(REPO, "instances", "schneider_evrptw")

# mean depot-customer distance of the synthetic instances is 46.5 (N=12) to
# 62.5 (N=20) and R_D = 160 is 2.56-3.44x that; 2.5 keeps the same regime
DRONE_RANGE_FACTOR = 2.5

FAMILIES = ["c101", "c201", "r101", "r201", "rc101", "rc201"]


def list_instances(suffix="_21"):
    """The 100-customer Schneider instances, e.g. c101_21."""
    out = []
    for name in sorted(os.listdir(INST_DIR)):
        if name.endswith(".txt") and name.endswith(suffix + ".txt"):
            out.append(name[:-4])
    return out


def node_number(node):
    """Numeric part of a node id ("C30" -> 30); accepts the node dict too."""
    node_id = node["id"] if isinstance(node, dict) else node
    m = re.search(r"(\d+)", node_id)
    return int(m.group(1)) if m else 0


def load(name):
    """Parse one Schneider instance with the existing reader."""
    return SE.parse_instance(os.path.join(INST_DIR, name + ".txt"))


def make_evrp(name="c101_21", n=None, start=0,
              drone_range_factor=DRONE_RANGE_FACTOR, cap_mode="file"):
    """Build a W6-compatible instance from a Schneider (2014) instance.

    n / start choose the customer subset (customers sorted by their id, the
    Solomon convention). cap_mode="file" uses the paper's load capacity C,
    "model" uses the W6 default CAP so only the geometry differs.
    Returns (inst, meta).
    """
    raw = load(name)
    customers = sorted(raw["customers"], key=node_number)
    if n is not None:
        customers = customers[start:start + n]
    stations = list(raw["stations"])

    coord = {0: (raw["depot"]["x"], raw["depot"]["y"])}
    demand, tw = {}, {}
    for i, c in enumerate(customers, start=1):
        coord[i] = (c["x"], c["y"])
        demand[i] = float(c["demand"])
        tw[i] = (float(c["ready"]), float(c["due"]))
    for j, s in enumerate(stations, start=len(customers) + 1):
        coord[j] = (s["x"], s["y"])

    mean_depot_dist = (sum(w6.dist({"coord": coord}, 0, i)
                           for i in range(1, len(customers) + 1))
                       / max(1, len(customers)))
    drone_range = drone_range_factor * mean_depot_dist

    Q = raw["params"]["Q"]
    r = raw["params"]["r"]
    g = raw["params"]["g"]
    service = float(customers[0]["serv"]) if customers else 0.0
    cap = float(raw["params"]["C"]) if cap_mode == "file" else w6.CAP

    inst = {
        "depot": coord[0],
        "customers": {i: coord[i] for i in range(1, len(customers) + 1)},
        "stations": {j: coord[j] for j in range(len(customers) + 1,
                                                 len(customers) + 1 + len(stations))},
        "tw": tw, "demand": demand, "coord": coord,
        "Q": Q / r,                 # battery = range in distance units
        "cap": cap,                 # load capacity (enforced)
        "service": service,         # minutes, per customer
        "recharge": Q * g,          # full charge from empty, minutes
        "drone_range": drone_range,
        "n": len(customers),
    }
    meta = {
        "name": name, "family": name.split("_")[0],
        "n": len(customers), "n_stations": len(stations),
        "total_demand": sum(demand.values()), "cap": cap,
        "battery_range": Q / r, "recharge_min": Q * g, "service_min": service,
        "mean_depot_dist": mean_depot_dist, "drone_range": drone_range,
        "paper_vehicles": raw["params"].get("m"),
    }
    return inst, meta


if __name__ == "__main__":
    inst, meta = make_evrp("c101_21", n=12)
    print("instance:", meta)
    print("customers:", len(inst["customers"]),
          "stations:", len(inst["stations"]))
    v1 = w6.run_variant(inst, "V1")
    v2 = w6.run_variant(inst, "V2")
    print(f"V1 mk={v1['makespan']:.1f} feasible={v1['feasible']} "
          f"tw_viol={v1['tw_viol']} rechg={v1['recharges']}")
    print(f"V2 mk={v2['makespan']:.1f} feasible={v2['feasible']} "
          f"off={v2['offloaded']} tw_viol={v2['tw_viol']}")
