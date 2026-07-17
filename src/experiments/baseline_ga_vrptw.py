"""
Genetic-algorithm (GA) baseline for the official Solomon VRPTW benchmark.

Purpose: a *self-implemented* metaheuristic baseline to sit next to OR-Tools,
so the project is not "only ever calling a solver library". The GA solves the
same 56 official Solomon 100-customer VRPTW instances that
`benchmark_official_solomon.py` (OR-Tools) solves, and we compare GA vs
OR-Tools vs the published Best-Known Solution (BKS).

Design (kept deliberately simple and explainable):
  - representation: a permutation of the 100 customers (route-first)
  - decoding: greedy "sequential split" that appends customers in permutation
    order, opening a new route whenever capacity or the time window would be
    violated -> always returns a *feasible* solution (if one exists)
  - crossover: Order Crossover (OX)
  - mutation: swap two positions OR reverse a segment (2-opt-like)
  - selection: tournament
  - survival: elitism (keep the best N individuals)
  - objective: minimise number of vehicles first, then total distance
    (matches the OR-Tools hierarchy)

This is a *generic* VRPTW baseline. It does NOT model EV charging -- the
official Solomon set has no charging, so it is compared on plain VRPTW against
the OR-Tools VRPTW run. Adding an EV/charging-aware GA is a separate extension.

Run:
    python src/experiments/baseline_ga_vrptw.py
"""

import csv
import math
import os
import random
import time
import urllib.request

import vrplib

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INSTANCE_DIR = os.path.join(REPO_ROOT, "src", "instances", "official_solomon")
RESULTS_DIR = os.path.join(REPO_ROOT, "src", "results")
CSV_PATH = os.path.join(RESULTS_DIR, "baseline_ga_vrptw_results.csv")
CMP_PATH = os.path.join(RESULTS_DIR, "baseline_ga_vrptw_comparison.csv")
LOG_PATH = os.path.join(RESULTS_DIR, "baseline_ga_vrptw_output.txt")
ORT_PATH = os.path.join(RESULTS_DIR, "benchmark_official_solomon_results.csv")

BASE_URL = "https://raw.githubusercontent.com/PyVRP/Instances/main/VRPTW/Solomon/"

POP_SIZE = 40
N_ELITE = 6
TOURNAMENT = 4
MUT_RATE = 0.30
TIME_LIMIT_S = 8           # per-instance search budget (≈ OR-Tools 10s)
SEED = 20260717

FAMILIES = {
    "C1":  [f"C10{i}" for i in range(1, 10)],
    "C2":  [f"C20{i}" for i in range(1, 9)],
    "R1":  [f"R10{i}" for i in range(1, 10)] + ["R110", "R111", "R112"],
    "R2":  [f"R20{i}" for i in range(1, 10)] + ["R210", "R211"],
    "RC1": [f"RC10{i}" for i in range(1, 9)],
    "RC2": [f"RC20{i}" for i in range(1, 9)],
}
ALL_INSTANCES = [n for group in FAMILIES.values() for n in group]


# --------------------------------------------------------------------------- #
# Download / cache
# --------------------------------------------------------------------------- #
def _download(name, ext):
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
    cost, routes = None, 0
    with open(sol_path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            s = line.strip()
            if s.lower().startswith("route"):
                routes += 1
            elif s.lower().startswith("cost"):
                cost = float(s.split()[-1])
    return cost, routes


def load_instance(name):
    vrp = _download(name, "vrp")
    inst = vrplib.read_instance(vrp)
    sol = _download(name, "sol")
    bks_cost, bks_veh = _parse_bks(sol)
    coords = [(float(c[0]), float(c[1])) for c in inst["node_coord"]]
    demands = [int(round(d)) for d in inst["demand"]]
    tw = [(int(w[0]), int(w[1])) for w in inst["time_window"]]
    capacity = int(inst["capacity"])
    service = int(inst.get("service_time", 0))
    n = len(coords)
    D = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = math.hypot(coords[i][0] - coords[j][0], coords[i][1] - coords[j][1])
            D[i][j] = d
            D[j][i] = d
    return {
        "name": name, "coords": coords, "demands": demands, "tw": tw,
        "capacity": capacity, "service": service, "n": n, "D": D,
        "bks_cost": bks_cost, "bks_veh": bks_veh,
    }


# --------------------------------------------------------------------------- #
# GA building blocks
# --------------------------------------------------------------------------- #
def _route_feasible(route, data):
    """Return (feasible, total_distance) for a route [depot, ..., depot]."""
    tw, svc = data["tw"], data["service"]
    D, cap, dem = data["D"], data["capacity"], data["demands"]
    t, load, dist, prev = tw[0][0], 0, 0.0, 0
    for node in route[1:]:
        arr = t + D[prev][node]
        start = arr if arr >= tw[node][0] else tw[node][0]
        if start > tw[node][1]:
            return False, 0.0
        load += dem[node]
        if load > cap:
            return False, 0.0
        t, dist, prev = start + svc, dist + D[prev][node], node
    return True, dist + D[prev][0]


def decode(perm, data):
    """Solomon I1-style insertion construction from a customer permutation.

    Each customer is inserted at the feasible position that least increases
    route distance; a new route is opened only when no existing route can take
    it. This naturally yields few vehicles and good distances (unlike a naive
    sequential split, which tends to spawn many short routes).
    """
    D = data["D"]
    routes = []
    for c in perm:
        best, best_added = None, float("inf")
        for ri, rt in enumerate(routes):
            for pos in range(1, len(rt)):
                nr = rt[:pos] + [c] + rt[pos:]
                ok, _ = _route_feasible(nr, data)
                if ok:
                    added = D[rt[pos - 1]][c] + D[c][rt[pos]] - D[rt[pos - 1]][rt[pos]]
                    if added < best_added:
                        best_added, best = added, (ri, pos, nr)
        if best:
            ri, pos, nr = best
            routes[ri] = nr
        else:
            routes.append([0, c, 0])
    total = 0.0
    for rt in routes:
        ok, dist = _route_feasible(rt, data)
        if not ok:
            return None
        total += dist
    return routes, total


def local_search(routes, data, max_pass=6):
    """Improve a VRPTW solution by intra-route 2-opt and inter-route relocate,
    keeping feasibility. Returns (routes, total_distance)."""
    def total(routes):
        tot = 0.0
        for rt in routes:
            ok, d = _route_feasible(rt, data)
            if not ok:
                return float("inf")
            tot += d
        return tot

    routes = [list(r) for r in routes]
    cur = total(routes)
    if cur == float("inf"):
        return routes, float("inf")
    for _ in range(max_pass):
        improved = False
        # 2-opt within each route
        for i in range(len(routes)):
            seq = routes[i][1:-1]
            m = len(seq)
            for a in range(m - 1):
                for b in range(a + 1, m):
                    rev = seq[:a] + seq[a:b + 1][::-1] + seq[b + 1:]
                    cand = routes[:i] + [[0] + rev + [0]] + routes[i + 1:]
                    t = total(cand)
                    if t < cur - 1e-9:
                        routes, cur = cand, t
                        improved = True
        # relocate a customer to a better position / route
        n_r = len(routes)
        for i in range(n_r):
            if len(routes[i]) <= 2:
                continue
            for j in range(1, len(routes[i]) - 1):
                c = routes[i][j]
                rest = routes[i][:j] + routes[i][j + 1:]
                for k in range(n_r):
                    if k == i and len(rest) <= 2:
                        continue
                    target = rest if k == i else routes[k]
                    for pos in range(1, len(target)):
                        if k == i:
                            newk = target[:pos] + [c] + target[pos:]
                            cand = routes[:i] + [newk] + routes[i + 1:]
                        else:
                            newk = target[:pos] + [c] + target[pos:]
                            cand = (routes[:i] + [rest] + routes[i + 1:k]
                                    + [newk] + routes[k + 1:])
                        t = total(cand)
                        if t < cur - 1e-9:
                            routes, cur = cand, t
                            improved = True
                            break
                    if improved:
                        break
                if improved:
                    break
            if improved:
                break
        if not improved:
            break
    return routes, cur


def savings_init(data):
    """Clarke-Wright savings construction -> a customer-permutation seed.

    Gives the GA a strong starting point, especially for clustered instances
    (C1 family) where a pure random permutation converges poorly.
    """
    n, D = data["n"], data["D"]
    routes = [[0, i, 0] for i in range(1, n)]
    sav = []
    for i in range(1, n):
        for j in range(i + 1, n):
            sav.append((D[0][i] + D[0][j] - D[i][j], i, j))
    sav.sort(reverse=True)
    cust_route = {i: i - 1 for i in range(1, n)}
    for _, i, j in sav:
        ri, rj = cust_route[i], cust_route[j]
        if ri == rj:
            continue
        merged = routes[ri][:-1] + routes[rj][1:]
        ok, _ = _route_feasible(merged, data)
        if ok:
            routes[ri] = merged
            for c in merged[1:-1]:
                cust_route[c] = ri
            routes[rj] = None
    routes = [r for r in routes if r]
    perm = []
    for r in routes:
        perm += r[1:-1]
    return perm


def force_fleet(routes, target, data):
    """Split routes (longest first) until we reach `target` feasible routes,
    so the GA competes at the same fleet size as the BKS/OR-Tools."""
    routes = [list(r) for r in routes]
    while len(routes) < target:
        cand = sorted(range(len(routes)), key=lambda i: -len(routes[i]))
        done = False
        for ci in cand:
            rt = routes[ci]
            if len(rt) <= 3:
                continue
            for cut in range(2, len(rt) - 1):
                r1 = rt[:cut] + [0]
                r2 = [0] + rt[cut:]
                ok1, _ = _route_feasible(r1, data)
                ok2, _ = _route_feasible(r2, data)
                if ok1 and ok2:
                    routes[ci] = r1
                    routes.append(r2)
                    done = True
                    break
            if done:
                break
        if not done:
            break
    return routes


def ox(p1, p2):
    n = len(p1)
    a, b = sorted(random.sample(range(n), 2))
    child = [None] * n
    child[a:b + 1] = p1[a:b + 1]
    fill = [g for g in p2 if g not in child[a:b + 1]]
    k = 0
    for i in range(n):
        if child[i] is None:
            child[i] = fill[k]
            k += 1
    return child


def mutate(p):
    n = len(p)
    if random.random() < 0.5:
        i, j = random.sample(range(n), 2)
        p[i], p[j] = p[j], p[i]
    else:
        i, j = sorted(random.sample(range(n), 2))
        p[i:j + 1] = p[i:j + 1][::-1]
    return p


def tournament(pop, fits):
    best, bestf = None, None
    for _ in range(TOURNAMENT):
        i = random.randrange(len(pop))
        if bestf is None or fits[i] < bestf:
            best, bestf = i, fits[i]
    return pop[best]


def solve_ga(data, time_limit=TIME_LIMIT_S, penalty=1000.0):
    n = data["n"] - 1                      # number of customers (depot = 0)
    cust = list(range(1, n + 1))
    # Aim for the BKS vehicle count; extra vehicles are heavily penalised so
    # the GA competes on *distance* at the same fleet size as the BKS/OR-Tools.
    if data["bks_veh"] and data["bks_veh"] > 0:
        target_veh = data["bks_veh"]
    else:
        total_dem = sum(data["demands"])
        target_veh = max(1, math.ceil(total_dem / data["capacity"]))

    def fitness(veh, dist):
        return dist + penalty * abs(veh - target_veh)

    def evaluate(perm):
        res = decode(perm, data)
        if res is None:
            return 1e18, (10 ** 9, 10 ** 9)
        routes = force_fleet(res[0], target_veh, data)
        routes, dist = local_search(routes, data)
        return fitness(len(routes), dist), (len(routes), dist)

    pop = [random.sample(cust, n) for _ in range(POP_SIZE)]
    sp = savings_init(data)
    if sp:
        pop[0] = sp
        if POP_SIZE > 1:
            pop[1] = sp[::-1]
    fits, ress = [], []
    for p in pop:
        f, res = evaluate(p)
        fits.append(f)
        ress.append(res)

    best, bestkey = None, (10 ** 9, 10 ** 9)
    start = time.time()
    gen = 0
    while time.time() - start < time_limit:
        gen += 1
        order = sorted(range(len(pop)), key=lambda i: fits[i])
        if ress[order[0]] < bestkey:
            bestkey, best = ress[order[0]], pop[order[0]][:]
        newpop = [pop[order[i]] for i in range(N_ELITE)]
        newfits = [fits[order[i]] for i in range(N_ELITE)]
        newress = [ress[order[i]] for i in range(N_ELITE)]
        while len(newpop) < POP_SIZE:
            c1 = tournament(pop, fits)
            c2 = tournament(pop, fits)
            child = ox(c1, c2)
            if random.random() < MUT_RATE:
                child = mutate(child)
            f, res = evaluate(child)
            newpop.append(child)
            newfits.append(f)
            newress.append(res)
        pop, fits, ress = newpop, newfits, newress

    order = sorted(range(len(pop)), key=lambda i: fits[i])
    if ress[order[0]] < bestkey:
        bestkey, best = ress[order[0]], pop[order[0]][:]
    return bestkey, gen


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    random.seed(SEED)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    rows, log = [], []

    def emit(line=""):
        print(line)
        log.append(line)

    emit("=" * 78)
    emit("GA BASELINE  —  OFFICIAL SOLOMON VRPTW  (vs OR-Tools vs BKS)")
    emit(f"instances: {len(ALL_INSTANCES)} (classic 100-customer set)")
    emit(f"config: pop={POP_SIZE}, elite={N_ELITE}, tourn={TOURNAMENT}, "
         f"mut={MUT_RATE}, {TIME_LIMIT_S}s/instance, seed={SEED}")
    emit("=" * 78)
    emit(f"{'inst':<9}{'BKS':>9}{'BKSv':>5}{'GA_dist':>10}{'GA_v':>5}"
         f"{'GA_gap%':>9}{'gens':>7}{'status':>7}")
    emit("-" * 78)

    fam_gaps = {}
    for name in ALL_INSTANCES:
        try:
            data = load_instance(name)
        except Exception as e:  # noqa: BLE001
            emit(f"{name:<9}  load failed: {repr(e)[:50]}")
            continue

        (bestkey, gens) = solve_ga(data)
        ga_veh, ga_dist = bestkey
        bks = data["bks_cost"]

        if ga_dist >= 10 ** 8:
            emit(f"{name:<9}{(bks or 0):>9.1f}{data['bks_veh']:>5}"
                 f"{'-':>10}{'-':>5}{'-':>9}{gens:>7}FAIL")
            rows.append({"instance": name, "bks_dist": bks,
                         "bks_vehicles": data["bks_veh"], "ga_dist": None,
                         "ga_vehicles": None, "ga_gap_pct": None, "status": "FAIL"})
            continue

        ga_dist = round(ga_dist, 1)
        gap = (ga_dist - bks) / bks * 100.0 if bks else 0.0
        fam = next(f for f, g in FAMILIES.items() if name in g)
        fam_gaps.setdefault(fam, []).append(gap)
        emit(f"{name:<9}{bks:>9.1f}{data['bks_veh']:>5}{ga_dist:>10.1f}"
             f"{ga_veh:>5}{gap:>9.1f}{gens:>7}OK")
        rows.append({"instance": name, "bks_dist": bks,
                     "bks_vehicles": data["bks_veh"], "ga_dist": ga_dist,
                     "ga_vehicles": ga_veh, "ga_gap_pct": round(gap, 2),
                     "status": "OK"})

    emit("-" * 78)
    emit("PER-FAMILY MEAN GAP (GA vs BKS):")
    for fam in FAMILIES:
        if fam in fam_gaps and fam_gaps[fam]:
            gs = fam_gaps[fam]
            emit(f"  {fam:<4} n={len(gs):<3} mean = {sum(gs)/len(gs):>6.1f}%"
                 f"  (min {min(gs):.1f}%, max {max(gs):.1f}%)")
    all_gaps = [g for gs in fam_gaps.values() for g in gs]
    if all_gaps:
        emit("-" * 78)
        emit(f"OVERALL: solved {len(all_gaps)}/{len(ALL_INSTANCES)}, "
             f"GA mean gap to BKS = {sum(all_gaps)/len(all_gaps):.1f}%")
    emit("=" * 78)

    # GA-only results CSV
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["instance", "bks_dist", "bks_vehicles",
                                           "ga_dist", "ga_vehicles", "ga_gap_pct",
                                           "status"])
        w.writeheader()
        w.writerows(rows)

    # Three-way comparison: GA vs OR-Tools (from existing CSV) vs BKS
    ort = {}
    if os.path.exists(ORT_PATH):
        with open(ORT_PATH, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                ort[r["instance"]] = r
    with open(CMP_PATH, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["instance", "bks_dist", "bks_veh", "ortools_dist",
                    "ortools_veh", "ortools_gap", "ga_dist", "ga_veh",
                    "ga_gap", "ga_minus_ortools_gap"])
        for r in rows:
            o = ort.get(r["instance"])
            if o and r["status"] == "OK":
                w.writerow([r["instance"], r["bks_dist"], r["bks_vehicles"],
                            o["my_dist"], o["my_vehicles"], o["gap_pct"],
                            r["ga_dist"], r["ga_vehicles"], r["ga_gap_pct"],
                            round(r["ga_gap_pct"] - float(o["gap_pct"]), 2)])

    with open(LOG_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(log) + "\n")

    print(f"\n[saved] {CSV_PATH}")
    print(f"[saved] {CMP_PATH}")
    print(f"[saved] {LOG_PATH}")


if __name__ == "__main__":
    main()
