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
  truck at a later node (the truck waits). Each drone executes its own sorties
  in launch order; if a drone is still airborne when the truck reaches the
  recovery node, the truck waits.
- **Key design**: the route lists **customers only** (plus the depot bookends)
  and the charging detours are inserted by the evaluator at evaluation time.
  That lets the week08_lns destroy/repair be reused unchanged, with only the
  evaluator swapped.
- **Objective**: the LNS uses `makespan + 1000 * TW violations`, rejecting
  energy-infeasible states; the reported numbers come from the full evaluator
  (true makespan, violation count, recharge count).

Three variants:

- **V1**: electric truck only (week06 `truck_ev_route`) -- the EV baseline
- **V3g**: electric truck + drone (K=1), greedy
- **V3l**: electric truck + drone (K=1/2/3), greedy + LNS

## 3. Results (10 seeds per size)

V1 truck-only EV makespan, and the V3 LNS solution under each drone count K.
Parentheses show the reduction vs V1; for K>1 the extra reduction vs K=1 is
also given.

| size | V1 truck EV | V3g | V3l K=1 | V3l K=2 | V3l K=3 |
|---|---:|---:|---:|---:|---:|
| N=8  | 485.8 | 257.8 (46.4%) | 225.3 (**53.4%**) | 176.0 (63.5%, +21.5% vs K1) | 131.5 (**72.8%**, +41.5% vs K1) |
| N=12 | 694.7 | 415.1 (40.1%) | 386.8 (44.4%) | 292.6 (57.7%, +22.9% vs K1) | 220.8 (68.0%, +41.9% vs K1) |
| N=16 | 975.9 | 628.7 (35.6%) | 606.1 (37.7%) | 499.6 (48.7%, +17.4% vs K1) | 399.4 (59.0%, +33.8% vs K1) |
| N=20 | 1283.6 | 918.9 (27.9%) | 832.8 (34.7%) | 817.7 (35.9%, +1.7% vs K1) | 669.6 (47.2%, +19.5% vs K1) |

Time-window violations and recharge counts (V1 -> V3l, by K):

| size | V1 viol / rechg | K1 viol / rechg | K2 viol / rechg | K3 viol / rechg |
|---|---:|---:|---:|---:|
| N=8  | 2.4 / 0.9 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| N=12 | 6.0 / 1.3 | 0.8 / 0.2 | 0.1 / 0.0 | 0.0 / 0.0 |
| N=16 | 9.6 / 2.1 | 3.9 / 1.0 | 2.1 / 0.7 | 0.6 / 0.4 |
| N=20 | 13.5 / 2.9 | 7.5 / 1.5 | 4.4 / 1.5 | 3.0 / 1.3 |

LNS adds another 1.96%~11.64% over the greedy (K=1); it keeps paying off under
multiple drones.

## 4. What it shows

- **With the electric and time-window constraints the collaboration gain is
  still larger than under FSTSP**: V3l K=1 is 34.7%~53.4% below the truck-only
  EV, while the same family of methods gains only about 23%~45% over truck-only
  in the FSTSP setting (no battery, no time windows). K=2/3 push the gain to
  57.7%~72.8%.
- The reason is that **offloading to the drone shortens the truck route, which
  removes most charging detours and most late arrivals**: V1 needs 0.9-2.9
  recharges and has 2.4-13.5 violations on average; V3l needs 0-1.5 recharges
  and has 0-7.5 violations. The battery and time-window constraints therefore
  **amplify the value of the drone** rather than merely making the problem
  harder.
- **The marginal gain of adding drones diminishes with size**: at N=8 the K1->K3
  gain nearly doubles the benefit (53.4%->72.8%), but by N=20 it saturates
  (K1->K2 only +1.7%). Small, dispersed instances benefit most from more drones.
- The LNS keeps paying off in the EV+TW setting too (another 1.96%-11.64% below
  the greedy), consistent with the FSTSP-setting conclusion.

## 5. Model correction (found while extending V3 to multiple drones)

The original single-drone evaluator used `arr[i_pos]` (the truck's arrival at
the launch node) as the launch time and **did not track the single drone's own
availability**, so it allowed one drone to "serve" several sorties at the same
time -- physically impossible for a single drone, and it understated the
makespan (the previously reported single-drone 56.7%~87.8% came from this
defect). After switching to sequential assignment by recovery time, the true
single-drone reduction is 34.7%~53.4% (K=1 in the table above). The multiple
(K=2/3) results were already sequential and are unaffected; they are newly added
correct figures. The core FSTSP line (week06/08) uses the separate, correct
`drone_scheduling` scheduler and was never affected.

## 6. Validation and limitations

- **Validation**: every solution is checked to serve all customers (truck route
  union drone sorties = all customers) and to be energy-feasible -- passed;
  K=1 matches the pre-correction single-drone evaluator in feasibility
  structure (only the launch-time semantics were corrected).
- Limitations: time windows are a penalty in the search rather than a hard
  constraint (so a few violations can remain, and the count is reported);
  recharging is the simplified "full recharge at a station", not partial
  charging; V3 is tested with up to K=3 drones and not larger K.

## 7. Artifacts

- `src/experiments/v3_ev_collab.py`: EV/TW/drone evaluator (K drones) + greedy + experiment
- `src/results/v3_ev_collab_raw.csv` / `_summary.csv` / `_log.txt`
