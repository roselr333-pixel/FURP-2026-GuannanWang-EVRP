"""
Murray & Chu (2015) FSTSP benchmark instances -- the ORIGINAL files.

Source: the instance set distributed with Dell'Amico, Montemanni & Novellani
("Exact models for the FSTSP"), downloaded from
https://www.or.unimore.it/site/home/online-resources/exact-models-for-the-fstsp/
and stored under src/instances/murray_chu_2015/.

Layout (per the README-datafile_descriptions.xlsx shipped in the archive):
  nodes.csv    : node id, x, y, isTooHeavy (for node 0 this column holds the
                 UAV speed in miles/minute)
  tau.csv      : a travel-time matrix
  tauprime.csv : the other travel-time matrix
  Cprime.csv   : the customers light enough to be served by the UAV
  FSTSP_OFV.csv: the objective value reported in the literature (when present)
  node 0 = starting depot, 1..c = customers, c+1 = ending depot

Which matrix is the truck and which is the UAV is NOT stated in the README.
`calibrate()` decides it from the data: the UAV is the faster vehicle in the
FSTSP, and the assignment that lets the drone actually pay off (i.e. that makes
the literature OFV reachable) is the truck = the slower matrix.

Because both matrices are (numerically) a constant multiple of the Euclidean
distance, the model can also be run through the usual speed-based harness by
setting the two speeds accordingly (`implied_speeds`).

Run (self-test / calibration):
  python src/experiments/fstsp_mc.py
"""

import os
import csv
import math
import statistics

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(_HERE))
MC_DIR = os.path.join(REPO, "src", "instances", "murray_chu_2015",
                      "Murray_Chu_2015_test_data", "FSTSP",
                      "FSTSP_10_customer_problems")


def list_instances():
    return sorted(d for d in os.listdir(MC_DIR) if d.startswith("2014"))


def load_mc(name):
    """Load one M&C instance. Returns a dict with coordinates, the two time
    matrices, the UAV-eligible customers and the literature OFV (or None)."""
    d = os.path.join(MC_DIR, name)
    nodes = [[c.strip() for c in r]
             for r in csv.reader(open(os.path.join(d, "nodes.csv"), encoding="utf-8")) if r]
    tau = [[float(x) for x in r]
           for r in csv.reader(open(os.path.join(d, "tau.csv"), encoding="utf-8")) if r]
    taup = [[float(x) for x in r]
            for r in csv.reader(open(os.path.join(d, "tauprime.csv"), encoding="utf-8")) if r]
    cprime = [int(x) for x in next(csv.reader(
        open(os.path.join(d, "Cprime.csv"), encoding="utf-8")))]
    ofv = None
    p = os.path.join(d, "FSTSP_OFV.csv")
    if os.path.exists(p):
        txt = open(p, encoding="utf-8").read().strip()
        if txt:
            ofv = float(txt)

    end = len(nodes) - 1                      # c+1 == ending depot
    customers = list(range(1, end))
    coord = {0: (float(nodes[0][1]), float(nodes[0][2]))}
    for i in customers:
        coord[i] = (float(nodes[i][1]), float(nodes[i][2]))
    # node c+1 is the ending depot: same place as node 0
    coord[end] = coord[0]
    return {
        "name": name, "n": len(customers), "customers": customers,
        "coord": coord, "depot": coord[0],
        "tau": tau, "tauprime": taup, "end": end,
        "drone_ok": set(cprime),
        "uav_speed_declared": float(nodes[0][3]),
        "ofv": ofv,
    }


def euclid(inst, i, j):
    a, b = inst["coord"][i], inst["coord"][j]
    return math.hypot(a[0] - b[0], a[1] - b[1])


def implied_speeds(inst):
    """Both matrices are a constant multiple of the Euclidean distance, so each
    implies a speed. Returns (speed_from_tau, speed_from_tauprime)."""
    n = inst["end"] + 1
    rt, rp = [], []
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            d = euclid(inst, i, j)
            if d < 1e-9:
                continue
            rt.append(inst["tau"][i][j] / d)
            rp.append(inst["tauprime"][i][j] / d)
    mt, mp = statistics.median(rt), statistics.median(rp)
    return 1.0 / mt, 1.0 / mp, (min(rt), max(rt)), (min(rp), max(rp))


def calibrate():
    """Decide which matrix is the truck. The FSTSP drone is the faster vehicle;
    report both implied speeds and the spread of the ratio to distance."""
    for name in list_instances()[:3]:
        inst = load_mc(name)
        st, sp, rt, rp = implied_speeds(inst)
        print(f"{name}: speed(tau)={st:.4f} [ratio {rt[0]:.3f}-{rt[1]:.3f}]  "
              f"speed(tauprime)={sp:.4f} [ratio {rp[0]:.3f}-{rp[1]:.3f}]  "
              f"uav_declared={inst['uav_speed_declared']}")
        print(f"   -> faster vehicle = {'tau' if st > sp else 'tauprime'}")


# ---------------------------------------------------------------------------
# matrix-based FSTSP evaluator (single truck + K serial drones)
# ---------------------------------------------------------------------------
def mc_simulate(inst, route, trips, truck_m, drone_m, K=1, service=0.0):
    """Completion time using the M&C time matrices.

    route   : [0, ...truck customers..., end]  (depot bookends)
    trips   : (launch, (customers...), recover)
    Any customer not in inst['drone_ok'] served by a drone is infeasible."""
    for _, custs, _ in trips:
        for c in custs:
            if c not in inst["drone_ok"]:
                return None
    end = inst["end"]

    def idx(node, role):
        if node == 0:
            return 0
        if node == end:
            return len(route) - 1
        return route.index(node)

    arr = [0.0] * len(route)
    for p in range(1, len(route)):
        arr[p] = arr[p - 1] + truck_m[route[p - 1]][route[p]] \
            + (service if route[p] != end else 0.0)

    avail = [0.0] * K
    for ln, custs, rn in sorted(trips, key=lambda t: idx(t[0], "launch")):
        i_pos, j_pos = idx(ln, "launch"), idx(rn, "recover")
        flight = 0.0
        prev = ln
        for c in custs:
            flight += drone_m[prev][c]
            flight += service
            prev = c
        flight += drone_m[prev][rn]
        starts = [max(arr[i_pos], avail[k]) for k in range(K)]
        k = min(range(K), key=lambda z: (starts[z], z))
        # the launch node comes before the recovery node, and the drone assigned
        # to this sortie has to be back on the truck when it reaches the launch
        # node -- one drone cannot fly two sorties at the same time
        if i_pos >= j_pos or starts[k] > arr[i_pos] + 1e-9:
            return None
        recovery = max(arr[j_pos], starts[k] + flight)
        avail[k] = recovery
        wait = recovery - arr[j_pos]
        if wait > 0:
            for p in range(j_pos, len(arr)):
                arr[p] += wait
    return arr[-1]


def mc_tsp(inst, truck_m, service=0.0):
    """Truck-only tour time using a nearest-neighbour order (cheap reference)."""
    remaining = list(inst["customers"])
    order, cur = [], 0
    while remaining:
        nxt = min(remaining, key=lambda c: truck_m[cur][c])
        order.append(nxt)
        cur = nxt
        remaining.remove(nxt)
    t = 0.0
    cur = 0
    for c in order:
        t += truck_m[cur][c] + service
        cur = c
    t += truck_m[cur][inst["end"]]
    return t


# ---------------------------------------------------------------------------
# exact truck-only tour (Held-Karp; these instances have 10 customers)
# ---------------------------------------------------------------------------
def mc_tsp_opt(inst, truck_m, service=0.0):
    custs = inst["customers"]
    end = inst["end"]
    n = len(custs)
    full = 1 << n
    INF = float("inf")
    dp = [[INF] * n for _ in range(full)]
    for k, c in enumerate(custs):
        dp[1 << k][k] = truck_m[0][c] + service
    for mask in range(full):
        row = dp[mask]
        for k in range(n):
            cur = row[k]
            if cur == INF:
                continue
            for j in range(n):
                if mask & (1 << j):
                    continue
                nm = mask | (1 << j)
                v = cur + truck_m[custs[k]][custs[j]] + service
                if v < dp[nm][j]:
                    dp[nm][j] = v
    last = full - 1
    return min(dp[last][k] + truck_m[custs[k]][end] for k in range(n))


def _max_flight(inst, drone_m, trips, service=0.0):
    worst = 0.0
    for ln, custs, rn in trips:
        t = 0.0
        prev = ln
        for c in custs:
            t += drone_m[prev][c] + service
            prev = c
        t += drone_m[prev][rn]
        worst = max(worst, t)
    return worst


# ---------------------------------------------------------------------------
# greedy drone offload (route-and-reassign) on the matrices
# ---------------------------------------------------------------------------
def mc_greedy(inst, K=1, max_cust=2, endurance=None, service=0.0):
    truck_m, drone_m = inst["tau"], inst["tauprime"]
    end = inst["end"]
    remaining = list(inst["customers"])
    order, cur = [], 0
    while remaining:
        nxt = min(remaining, key=lambda c: truck_m[cur][c])
        order.append(nxt)
        cur = nxt
        remaining.remove(nxt)
    route = [0] + order + [end]
    trips = []
    protected = set()      # launch/recover nodes may not later be offloaded

    def ok_endur(t):
        if endurance is None:
            return True
        return _max_flight(inst, drone_m, t, service) <= endurance + 1e-9

    while True:
        base = mc_simulate(inst, route, trips, truck_m, drone_m, K, service)
        best = None
        for i_pos in range(len(route) - 1):
            for j_pos in range(i_pos + 2, len(route)):
                ln, rn = route[i_pos], route[j_pos]
                cands = [c for c in route[i_pos + 1:j_pos]
                         if c in inst["drone_ok"] and c not in protected]
                if not cands:
                    continue
                subsets = [(c,) for c in cands]
                if max_cust >= 2:
                    for a in range(len(cands)):
                        for b in range(a + 1, len(cands)):
                            subsets.append((cands[a], cands[b]))
                            subsets.append((cands[b], cands[a]))
                for custs in subsets:
                    new_route = [x for x in route if x not in custs]
                    new_trips = trips + [(ln, custs, rn)]
                    if not ok_endur(new_trips):
                        continue
                    t = mc_simulate(inst, new_route, new_trips,
                                    truck_m, drone_m, K, service)
                    if t is None:
                        continue
                    gain = base - t
                    if gain > 1e-9 and (best is None or gain > best[0]):
                        best = (gain, ln, custs, rn)
        if best is None:
            break
        _, ln, custs, rn = best
        route = [x for x in route if x not in custs]
        trips.append((ln, custs, rn))
        protected.add(ln)
        protected.add(rn)
    return route, trips


# ---------------------------------------------------------------------------
# destroy-and-repair LNS on the matrices (same idea as week08_lns)
# ---------------------------------------------------------------------------
def mc_lns(inst, K=1, max_cust=2, iters=200, seed=0, endurance=None,
           service=0.0):
    import random
    rng = random.Random(seed)
    truck_m, drone_m = inst["tau"], inst["tauprime"]
    end = inst["end"]

    def ev(route, trips):
        t = mc_simulate(inst, route, trips, truck_m, drone_m, K, service)
        if t is None:
            return float("inf")
        if endurance is not None and \
                _max_flight(inst, drone_m, trips, service) > endurance + 1e-9:
            return float("inf")
        return t

    route, trips = mc_greedy(inst, K, max_cust, endurance, service)
    best_route, best_trips = route[:], list(trips)
    best_mk = cur = ev(route, trips)
    T = 0.05 * max(cur, 1.0)
    alpha = 0.001 ** (1.0 / max(1, iters))
    q_max = max(2, len(inst["customers"]) // 4)

    for _ in range(iters):
        q = rng.randint(1, q_max)
        chosen = rng.sample(inst["customers"], q)
        r2, t2 = route[:], list(trips)
        pending = set(chosen)
        for c in chosen:
            hit = False
            for idx in range(len(t2)):
                ln, custs, rn = t2[idx]
                if c in custs:
                    rest = tuple(x for x in custs if x != c)
                    t2[idx] = (ln, rest, rn) if rest else None
                    hit = True
                    break
            t2 = [t for t in t2 if t is not None]
            if hit:
                continue
            if c in r2:
                r2.remove(c)
            keep = []
            for ln, custs, rn in t2:
                if ln == c or rn == c:
                    pending.update(custs)
                else:
                    keep.append((ln, custs, rn))
            t2 = keep

        plist = list(pending)
        rng.shuffle(plist)
        feasible = True
        while plist:
            c = plist.pop(0)
            opts = []
            for p in range(1, len(r2)):
                opts.append(("truck", p, None, None))
            if c in inst["drone_ok"]:
                for i_pos in range(len(r2) - 1):
                    if r2[i_pos] == end:
                        continue
                    for j_pos in range(i_pos + 1, len(r2)):
                        pairs = [(c,)]
                        if max_cust >= 2:
                            pairs += [(c, c2) for c2 in plist]
                        for custs in pairs:
                            opts.append(("drone", i_pos, custs, j_pos))
            bestopt = (float("inf"), None, None, None, None)
            for kind, p, custs, j_pos in opts:
                if kind == "truck":
                    v = ev(r2[:p] + [c] + r2[p:], t2)
                else:
                    v = ev(r2, t2 + [(r2[p], custs, r2[j_pos])])
                if v < bestopt[0] - 1e-9:
                    bestopt = (v, kind, p, custs, j_pos)
            if bestopt[1] is None:
                feasible = False
                break
            _, kind, p, custs, j_pos = bestopt
            if kind == "truck":
                r2 = r2[:p] + [c] + r2[p:]
            else:
                t2 = t2 + [(r2[p], custs, r2[j_pos])]
                for x in custs:
                    if x in plist:
                        plist.remove(x)
        if not feasible:
            T *= alpha
            continue

        new_mk = ev(r2, t2)
        if new_mk - cur < -1e-9 or rng.random() < math.exp(
                -(new_mk - cur) / max(T, 1e-9)):
            route, trips, cur = r2, t2, new_mk
            if new_mk < best_mk - 1e-9:
                best_route, best_trips, best_mk = r2[:], list(t2), new_mk
        T *= alpha
    return best_route, best_trips, best_mk


if __name__ == "__main__":
    print("Murray & Chu (2015) instances found:", len(list_instances()))
    calibrate()
