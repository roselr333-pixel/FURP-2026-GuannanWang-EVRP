"""
Drone energy and payload model (extension).

The main line limits the drone with a single range constant R_D: a sortie's total
flight distance must not exceed 160. That treats the drone as non-electric, while
the project is about electric routing. This module adds the two limits a real
multi-rotor drone actually has:

  * a payload capacity P_MAX -- the total demand carried in one sortie;
  * an energy budget E_D -- the flight consumes energy at a rate that grows with
    the payload still on board:

        energy(sortie) = sum over legs of
                         (ALPHA + BETA * payload_on_that_leg) * leg_distance

    where payload_on_that_leg is the demand of the sortie's customers that have
    not been served yet when the drone leaves the leg's start node.

With BETA = 0 and E_D = R_D the energy budget is exactly the old range limit, so
this module reproduces the existing model; the self-test below checks that
against cpsat_fstsp.fstsp_makespan_clean on random plans.

Everything else is the same physical model as the main line: a launch precedes
its recovery, one serial drone (a sortie starts only after the previous one has
been recovered), the truck waits at the recovery node, and an infeasible sortie
set returns inf.

Contents
--------
  sortie_energy(inst, ln, custs, rn, ...)       energy of one sortie
  simulate(inst, route, trips, ...)             physical evaluator (ok, arr)
  makespan(inst, route, trips, ...)             completion time, inf if invalid
  greedy(inst, max_cust, multi_takeoff, ...)    the same route-and-reassign greedy

Run (self-test):
  python src/experiments/drone_energy.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import week06_ground_air_evrp_tw as w6

V_T = w6.V_T
V_D = w6.V_D
SERVICE = w6.SERVICE
R_D = w6.R_D

# --- the extension's parameters ---
ALPHA = 1.0          # energy per distance unit with no payload
BETA = 0.02          # extra energy per (distance unit x demand unit)
E_D = 160.0          # energy budget per sortie (= the old range when BETA = 0)
P_MAX = 30.0         # payload capacity of one sortie

INF = float("inf")


def _as_list(custs):
    return list(custs) if isinstance(custs, (list, tuple)) else [custs]


def sortie_energy(inst, ln, custs, rn, alpha=ALPHA, beta=BETA):
    """Energy of one sortie, with consumption growing with the load on board."""
    cl = _as_list(custs)
    legs = [ln] + cl + [rn]
    remaining = sum(inst["demand"][c] for c in cl)
    e = 0.0
    for k in range(len(legs) - 1):
        e += (alpha + beta * remaining) * w6.dist(inst, legs[k], legs[k + 1])
        if k < len(cl):
            remaining -= inst["demand"][legs[k + 1]]
    return e


def sortie_distance(inst, ln, custs, rn):
    cl = _as_list(custs)
    legs = [ln] + cl + [rn]
    return sum(w6.dist(inst, legs[k], legs[k + 1])
               for k in range(len(legs) - 1))


def simulate(inst, route, trips, alpha=ALPHA, beta=BETA, ed=E_D, p_max=P_MAX):
    """Truck arrival times for a physically valid, energy-feasible plan.

    Returns (ok, arr); ok is False when the plan is not realisable: launch not
    before recovery, payload above p_max, energy above ed, or a sortie launched
    before the drone is back on the truck.
    """
    arr = [0.0] * len(route)
    for p in range(1, len(route)):
        arr[p] = arr[p - 1] + w6.dist(inst, route[p - 1], route[p]) / V_T \
            + (SERVICE if route[p] != 0 else 0.0)

    ts = sorted(trips, key=lambda t: 0 if t[0] == 0 else route.index(t[0]))
    drone_free = 0.0
    for ln, cs, rn in ts:
        cl = _as_list(cs)
        i_pos = 0 if ln == 0 else route.index(ln)
        j_pos = len(route) - 1 if rn == 0 else route.index(rn)
        if i_pos >= j_pos:
            return False, None
        if sum(inst["demand"][c] for c in cl) > p_max + 1e-9:
            return False, None
        if sortie_energy(inst, ln, cl, rn, alpha, beta) > ed + 1e-9:
            return False, None
        if drone_free > arr[i_pos] + 1e-9:
            return False, None
        flight = sortie_distance(inst, ln, cl, rn) / V_D + SERVICE * len(cl)
        landing = arr[i_pos] + flight
        recovery = max(arr[j_pos], landing)
        wait = recovery - arr[j_pos]
        if wait > 0:
            for p in range(j_pos, len(arr)):
                arr[p] += wait
        drone_free = recovery
    return True, arr


def makespan(inst, route, trips, **kw):
    ok, arr = simulate(inst, route, trips, **kw)
    return arr[-1] if ok else INF


def greedy(inst, max_cust=2, multi_takeoff=True, **kw):
    """Route-and-reassign greedy, same loop as cpsat_fstsp.clean_greedy but every
    candidate is checked with the energy/payload evaluator."""
    all_c = list(inst["customers"].keys())
    route = [0] + w6.nn_order(inst, all_c) + [0]
    trips = []
    offloaded = set()
    protected = set()
    blocked = set()

    def usable(node):
        return multi_takeoff or node not in blocked

    while True:
        base = makespan(inst, route, trips, **kw)
        best = None
        for i in range(len(route) - 1):
            ln = route[i]
            if not usable(ln):
                continue
            for j in range(i + 2, len(route)):
                rn = route[j]
                if not usable(rn):
                    continue
                cands = [c for c in route[i + 1:j]
                         if c != 0 and c not in offloaded and c not in protected
                         and c not in blocked]
                if not cands:
                    continue
                subsets = [(c,) for c in cands]
                if max_cust >= 2 and len(cands) >= 2:
                    for a in range(len(cands)):
                        for b in range(a + 1, len(cands)):
                            subsets.append((cands[a], cands[b]))
                            subsets.append((cands[b], cands[a]))
                if max_cust >= 3 and len(cands) >= 3:
                    import itertools
                    for trio in itertools.combinations(cands, 3):
                        for perm in itertools.permutations(trio):
                            subsets.append(perm)
                for custs in subsets:
                    new_route = [x for x in route if x not in custs]
                    m = makespan(inst, new_route, trips + [(ln, custs, rn)],
                                 **kw)
                    if m == INF:
                        continue
                    gain = base - m
                    if gain > 1e-9 and (best is None or gain > best[0]):
                        best = (gain, ln, custs, rn)
        if best is None:
            break
        _, ln, custs, rn = best
        route = [x for x in route if x not in custs]
        trips.append((ln, custs, rn))
        offloaded.update(custs)
        protected.add(ln)
        protected.add(rn)
        if not multi_takeoff:
            blocked.add(ln)
            blocked.add(rn)
    return route, trips, offloaded


def _main():
    """Self-test: with BETA = 0 and a non-binding payload cap this must be exactly
    the range-only model (cpsat_fstsp.fstsp_makespan_clean)."""
    import random
    import cpsat_fstsp as X

    rng = random.Random(5)
    bad = feasible = 0
    for trial in range(300):
        n = rng.choice([8, 10, 12])
        inst = w6.make_instance(n, seed=7000 + trial)
        cust = list(inst["customers"].keys())
        rng.shuffle(cust)
        route = [0] + cust + [0]
        trips = []
        for _ in range(rng.randint(0, 3)):
            i = rng.randrange(0, len(route) - 2)
            j = rng.randrange(i + 1, len(route) - 1)
            cs = tuple(rng.sample(cust, rng.choice([1, 2])))
            trips.append((route[i], cs, route[j]))
        mine = makespan(inst, route, trips, beta=0.0, ed=R_D, p_max=1e9)
        ref = X.fstsp_makespan_clean(inst, route, trips, R_D)
        if not (mine == ref or (mine == INF and ref == INF)):
            bad += 1
            if bad <= 3:
                print("MISMATCH", n, route, trips, mine, ref)
        if mine != INF:
            feasible += 1
    print(f"range-only reduction: {feasible} feasible of 300 random plans, "
          f"mismatches={bad}")
    assert bad == 0, "energy model with BETA=0 does not reproduce the range model"

    # greedy must also match the range-only greedy when energy is non-binding
    for n in (8, 12):
        inst = w6.make_instance(n, seed=20260720)
        r1, t1, o1 = greedy(inst, max_cust=2, beta=0.0, ed=R_D, p_max=1e9)
        r2, t2, o2 = X.clean_greedy(inst, max_cust=2)
        assert abs(makespan(inst, r1, t1, beta=0.0, ed=R_D, p_max=1e9)
                   - X.fstsp_makespan_clean(inst, r2, t2)) < 1e-9, n
        print(f"greedy n={n}: range-only reduction matches "
              f"({o1} vs {o2} customers offloaded)")


if __name__ == "__main__":
    _main()
