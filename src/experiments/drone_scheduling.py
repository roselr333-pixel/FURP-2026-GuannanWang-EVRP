"""
Drone-to-sortie scheduling for the multi-drone truck-drone model.

`week07_fstsp_repro.fstsp_simulate_multi` assigns each sortie to the drone that
can start earliest (classic "list scheduling"). This module treats the
assignment as an explicit scheduling problem: given a fixed truck route and a
fixed SET of sorties, decide which of the K drones serves which sortie. Three
methods share one simulation so they are directly comparable:

  greedy  : assign each sortie (in launch order) to the earliest-available drone
            (identical to fstsp_simulate_multi -- the baseline rule).
  local   : start from greedy, then repeatedly reassign a single sortie to a
            different drone if it lowers the makespan (local search).
  optimal : exact minimum over all assignments, by branch and bound with a
            lower-bound prune (only run when the sortie count is small).

Because local starts from greedy, and optimal is the exact minimum, the three
satisfy greedy >= local >= optimal on every instance (used as a self-test).

Run (self-test):
  python src/experiments/drone_scheduling.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import week06_ground_air_evrp_tw as w6

V_D = w6.V_D
SERVICE = w6.SERVICE


def _base_arr(inst, route):
    arr = [0.0] * len(route)
    for p in range(1, len(route)):
        arr[p] = arr[p - 1] + w6.dist(inst, route[p - 1], route[p]) \
            + (SERVICE if route[p] != 0 else 0.0)
    return arr


def _sorted_trips(route, trips):
    def pos(ln):
        return 0 if ln == 0 else route.index(ln)
    return sorted(trips, key=lambda t: pos(t[0]))


def _legs_and_flight(inst, ln, cust, rn):
    cl = list(cust) if isinstance(cust, (list, tuple)) else [cust]
    legs = [ln] + cl + [rn]
    d = sum(w6.dist(inst, legs[p], legs[p + 1]) for p in range(len(legs) - 1))
    return d / V_D + SERVICE * len(cl)


def simulate(inst, route, trips_sorted, assign, K):
    """Makespan for an explicit drone assignment (assign[i] = drone of trip i)."""
    arr = _base_arr(inst, route)
    avail = [0.0] * K
    for idx, (ln, cust, rn) in enumerate(trips_sorted):
        d = assign[idx]
        i_pos = 0 if ln == 0 else route.index(ln)
        j_pos = len(route) - 1 if rn == 0 else route.index(rn)
        flight = _legs_and_flight(inst, ln, cust, rn)
        launch = max(arr[i_pos], avail[d])
        recovery = max(arr[j_pos], launch + flight)
        avail[d] = recovery
        wait = recovery - arr[j_pos]
        if wait > 0:
            for p in range(j_pos, len(arr)):
                arr[p] += wait
    return arr[-1]


def schedule_greedy(inst, route, trips, K):
    ts = _sorted_trips(route, trips)
    arr = _base_arr(inst, route)
    avail = [0.0] * K
    assign = []
    for (ln, cust, rn) in ts:
        i_pos = 0 if ln == 0 else route.index(ln)
        j_pos = len(route) - 1 if rn == 0 else route.index(rn)
        flight = _legs_and_flight(inst, ln, cust, rn)
        starts = [max(arr[i_pos], avail[k]) for k in range(K)]
        d = min(range(K), key=lambda k: (starts[k], k))
        launch = starts[d]
        recovery = max(arr[j_pos], launch + flight)
        avail[d] = recovery
        wait = recovery - arr[j_pos]
        if wait > 0:
            for p in range(j_pos, len(arr)):
                arr[p] += wait
        assign.append(d)
    return assign, arr[-1]


def schedule_local(inst, route, trips, K, max_passes=20):
    ts = _sorted_trips(route, trips)
    if not ts:
        return [], 0.0
    assign, best = schedule_greedy(inst, route, ts, K)
    for _ in range(max_passes):
        improved = False
        for i in range(len(ts)):
            cur = assign[i]
            for d in range(K):
                if d == cur:
                    continue
                trial = assign[:]
                trial[i] = d
                m = simulate(inst, route, ts, trial, K)
                if m < best - 1e-9:
                    assign, best, cur, improved = trial, m, d, True
        if not improved:
            break
    return assign, best


def schedule_optimal(inst, route, trips, K, node_limit=400000):
    """Exact minimum makespan over all assignments (branch and bound).

    Returns (assign, makespan, proven) where proven=False means the node limit
    was hit before the search completed (treat the makespan as an upper bound)."""
    ts = _sorted_trips(route, trips)
    T = len(ts)
    if T == 0:
        return [], 0.0, True
    best = [float("inf"), None]
    nodes = [0]
    proven = [True]

    def dfs(i, assign):
        if nodes[0] >= node_limit:
            proven[0] = False
            return
        nodes[0] += 1
        if i == T:
            m = simulate(inst, route, ts, assign, K)
            if m < best[0]:
                best[0], best[1] = m, assign[:]
            return
        for d in range(K):
            assign.append(d)
            # partial makespan (first i+1 sorties) is a lower bound on the full
            # makespan, so it prunes branches that already exceed the incumbent
            lb = simulate(inst, route, ts[:i + 1], assign, K)
            if lb < best[0] - 1e-9:
                dfs(i + 1, assign)
            assign.pop()

    dfs(0, [])
    return best[1], best[0], proven[0]


def main():
    import week07_fstsp_repro as f7
    import week07_improvement_ablation as ab
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import fstsp_instances as fi

    print("self-test: greedy==fstsp_makespan_multi, and greedy>=local>=optimal")
    for name in fi.FAMILIES:
        for n in [10, 20]:
            inst = fi.make_solomon_fstsp(name, n)
            route, trips, off = ab.my_v2_param(inst, max_cust=2,
                                               multi_takeoff=True)
            for K in [1, 2, 3]:
                g_assign, g = schedule_greedy(inst, route, trips, K)
                l_assign, l = schedule_local(inst, route, trips, K)
                o_assign, o, proven = schedule_optimal(inst, route, trips, K)
                ref = f7.fstsp_makespan_multi(inst, route, trips, K)
                ok = abs(g - ref) < 1e-9 and l <= g + 1e-9 and o <= l + 1e-9
                print(f"  {name} n={n} K={K}: greedy={g:8.2f} local={l:8.2f} "
                      f"optimal={o:8.2f} (proven={proven}) trips={len(trips)} "
                      f"{'OK' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
