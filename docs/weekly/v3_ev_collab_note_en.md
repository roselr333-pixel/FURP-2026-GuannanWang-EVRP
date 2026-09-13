# V3: electric truck + drone + charging stations + time windows

## 1. Motivation

All the W8 LNS / multi-drone results sit on the FSTSP evaluator: unlimited truck
range, no time windows, the only constraints being the drone range and the
rendezvous. This section puts the week06 **battery + charging stations + time
windows** back into the truck-drone model, and extends V3 from a single drone to
multiple drones (K=1/2/3).

## 2. Model and implementation

- **Electric truck**: battery capacity Q, consumption rho per distance unit;
  when the remaining charge is insufficient the truck detours to the nearest
  station for a full recharge (time RECHARGE). To stay consistent with the
  week06 V1 baseline, the same assumption is used: the truck can always reach
  the nearest station, and only a leg that a full battery cannot cover counts as
  energy-infeasible.
- **Time windows**: arriving early means waiting; arriving late counts as a
  violation.
- **Drones (K homogeneous)**: still range-limited and still recovered by the
  truck at a later node. Each drone executes its own sorties in launch order,
  and **a sortie launches when the truck reaches its launch node**: if the drone
  assigned to it is not back on the truck by then the whole plan is infeasible
  (the launch cannot simply be delayed, because the truck has already left that
  node). If a drone is still airborne when the truck reaches the recovery node,
  the truck waits.
- **Key design**: the route lists **customers only** (plus the depot bookends)
  and the charging detours are inserted by the evaluator at evaluation time.
  That lets the week08_lns destroy/repair be reused unchanged, with only the
  evaluator swapped.
- **Objective**: the LNS uses `makespan + 1000 * TW violations`, rejecting
  energy-infeasible or schedule-infeasible states; the reported numbers come from
  the full evaluator (true makespan, violation count, recharge count).

Three variants:

- **V1**: electric truck only (week06 `truck_ev_route`) -- the EV baseline
- **V3g**: electric truck + drone (K=1), greedy
- **V3l**: electric truck + drone (K=1/2/3), greedy + LNS

## 3. Results (10 seeds per size)

V1 truck-only EV makespan, and the V3 solution under each drone count K.
Parentheses show the reduction vs V1; for K>1 the extra reduction vs K=1 is also
given.

| Size | V1 truck EV | V3g | V3l K=1 | V3l K=2 | V3l K=3 |
|---|---:|---:|---:|---:|---:|
| N=8  | 485.8 | 293.6 (39.2%) | 230.6 (**52.4%**) | 170.8 (64.6%, +25.6% vs K1) | 133.4 (**72.5%**, +41.7% vs K1) |
| N=12 | 694.7 | 517.4 (25.4%) | 382.3 (45.0%) | 267.5 (61.4%, +28.8% vs K1) | 220.9 (68.1%, +41.2% vs K1) |
| N=16 | 975.9 | 693.9 (29.0%) | 590.4 (39.3%) | 505.6 (47.9%, +13.6% vs K1) | 429.8 (55.5%, +26.5% vs K1) |
| N=20 | 1283.6 | 1069.0 (16.3%) | 850.5 (33.5%) | 707.1 (44.5%, +16.0% vs K1) | 661.0 (48.3%, +21.0% vs K1) |

Time-window violations and recharge counts (V1 -> V3l, by K):

| Size | V1 viol / rechg | K1 viol / rechg | K2 viol / rechg | K3 viol / rechg |
|---|---:|---:|---:|---:|
| N=8  | 2.4 / 0.9 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| N=12 | 6.0 / 1.3 | 0.6 / 0.4 | 0.0 / 0.0 | 0.0 / 0.0 |
| N=16 | 9.6 / 2.1 | 4.2 / 1.0 | 2.3 / 0.8 | 0.7 / 0.8 |
| N=20 | 13.5 / 2.9 | 6.9 / 1.7 | 4.8 / 1.5 | 3.0 / 1.3 |

LNS adds another 12.9%-26.0% over the greedy (K=1), and it keeps paying off under
multiple drones.

## 4. What it shows

- **Under the electric and time-window constraints the collaboration gain is
  still above what the same family of methods reaches in the FSTSP setting**:
  V3l K=1 is **33.5%-52.4%** below the truck-only EV (N=20 to N=8), against about
  23%-45% over truck-only in the FSTSP setting. K=2/3 push the gain to
  **44.5%-72.5%**.
- The reason is that **offloading to the drone shortens the truck route, which
  removes most charging detours and most late arrivals**: V1 needs 0.9-2.9
  recharges and has 2.4-13.5 violations on average, while V3l K=1 needs 0-1.7
  recharges and has 0-6.9 violations. The battery and time-window constraints
  therefore **amplify the value of the drone** rather than merely making the
  problem harder.
- **The marginal gain of adding drones diminishes with size, but has not
  saturated**: at N=8 K1->K3 lifts the reduction from 52.4% to 72.5% (another
  +41.7% relative to K1), and at N=20 K1->K2 still adds +16.0% with a further
  +21.0% to K3. Small, dispersed instances benefit most from more drones.
- The LNS keeps paying off in the EV+TW setting too (another 12.9%-26.0% below
  the greedy), consistent with the FSTSP-setting conclusion.

## 5. Two evaluator corrections

This evaluator has been corrected twice, both times for the same class of
problem: treating one drone as if it could fly several sorties at once.

1. The original single-drone evaluator used `arr[i_pos]` (the truck's arrival at
   the launch node) as the launch time and did not track the drone's own
   availability, so one drone could "serve" two sorties at the same time and the
   makespan was understated (the earlier single-drone figures of 56.7%-87.8%
   came from this). It now assigns sorties sequentially through the per-drone
   recovery time `avail[d]`.
2. Sequential assignment was still missing one check: **whether the drone
   assigned to a sortie is back on the truck at the launch node**. Without it the
   code simply delayed the launch until the drone was free, although the truck had
   already left that node, so the plan could not be flown as described. The
   evaluator now treats `avail[d] > arr[i_pos]` (or a recovery before its launch)
   as infeasible, returning `schedule_inf` with an infinite makespan, and the
   greedy and the LNS reject such candidates (regression tests in
   `tests/test_evaluators.py`).

The true single-drone LNS reduction after both corrections is **33.5%-52.4%**
(K=1 in the table above). The core FSTSP line (week06/08) uses the separate
`week07_fstsp_repro.fstsp_simulate` and `drone_scheduling`, which were never
affected by this defect.

## 6. Validation and limitations

- **Validation**: every solution is checked to serve all customers (truck route
  union drone sorties = all customers), to be energy-feasible, and to satisfy the
  single-drone physical schedule (`schedule_inf = False`) -- passed. With an
  empty sortie set the evaluator reproduces the week06 truck-only EV route
  instance by instance on makespan, violations and recharge count.
- Limitations: time windows are a penalty in the search rather than a hard
  constraint (so a few violations can remain, and the count is reported);
  recharging is the simplified "full recharge at a station", not partial
  charging; V3 is tested with up to K=3 drones and not larger K.

## 7. Artifacts

- `src/experiments/v3_ev_collab.py`: EV/TW/drone evaluator (K drones) + greedy + experiment
- `src/results/v3_ev_collab_raw.csv` / `_summary.csv` / `_log.txt`
