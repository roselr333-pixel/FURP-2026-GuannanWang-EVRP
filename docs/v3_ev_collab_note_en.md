# V3: electric truck + drone + charging stations + time windows

## 1. Motivation

All the W8 LNS / multi-drone results sit on the FSTSP evaluator: unlimited truck
range, no time windows, the only constraints being the drone range and the
rendezvous. This section closes that limitation by putting the week06
**battery + charging stations + time windows** back into the truck-drone model.

## 2. Model and implementation

- **Electric truck**: battery capacity Q, consumption rho per distance unit;
  when the remaining charge is insufficient the truck detours to the nearest
  station for a full recharge (time RECHARGE). To stay consistent with the
  week06 V1 baseline, the same assumption is used: the truck can always reach
  the nearest station, and only a leg that a full battery cannot cover counts as
  energy-infeasible.
- **Time windows**: arriving early means waiting; arriving late counts as a
  violation.
- **Drone**: still range-limited and still recovered by the truck at a later
  node (the truck waits).
- **Key design**: the route lists **customers only** (plus the depot bookends)
  and the charging detours are inserted by the evaluator at evaluation time.
  That lets the week08_lns destroy/repair be reused unchanged, with only the
  evaluator swapped.
- **Objective**: the LNS uses `makespan + 1000 * TW violations`, rejecting
  energy-infeasible states; the reported numbers come from the full evaluator
  (true makespan, violation count, recharge count).

Three variants:
- **V1**: electric truck only (week06 `truck_ev_route`) -- the EV baseline
- **V3g**: electric truck + drone, greedy
- **V3l**: electric truck + drone, greedy + LNS

## 3. Results (10 seeds per size)

| size | V1 truck EV | V3g | V3l | V3l vs V1 | LNS vs greedy | V1 TW viol | V3l viol | V1 recharges | V3l recharges |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| N=8 | 485.8 | 136.5 | **67.8** | **86.0%** | 47.9% | 2.4 | **0.0** | 0.9 | **0.0** |
| N=12 | 694.7 | 201.1 | **84.0** | **87.8%** | 57.3% | 6.0 | **0.0** | 1.3 | **0.0** |
| N=16 | 975.9 | 427.5 | **260.6** | **73.3%** | 38.9% | 9.6 | **0.0** | 2.1 | **0.2** |
| N=20 | 1283.6 | 716.4 | **551.7** | **56.7%** | 23.3% | 13.5 | **1.0** | 2.9 | **1.3** |

## 4. What it shows

- **With the electric and time-window constraints the collaboration gain is far
  larger than under FSTSP**: V3l is 56.7%~87.8% below the truck-only EV, while
  the same family of methods gains only about 23%~45% over truck-only in the
  FSTSP setting (no battery, no time windows).
- The reason is that **offloading to the drone shortens the truck route, which
  removes most charging detours and most late arrivals**: V1 needs 0.9-2.9
  recharges and has 2.4-13.5 violations on average; V3l needs 0-1.3 recharges
  and has 0-1.0 violations. The battery and time-window constraints therefore
  **amplify the value of the drone** rather than merely making the problem
  harder.
- The LNS keeps paying off in the EV+TW setting too (another 23.3%-57.3% below
  the greedy), consistent with the FSTSP-setting conclusion.

## 5. Validation and limitations

- **Validation**: every solution is checked to serve all customers (truck route
  union drone sorties = all customers) and to be energy-feasible -- passed.
- Limitations: V3 is still **single-drone** (multi-drone is not yet wired into
  the EV+TW model); time windows are a penalty in the search rather than a hard
  constraint (so a few violations can remain, and the count is reported);
  recharging is the simplified "full recharge at a station", not partial
  charging.

## 6. Artifacts

- `src/experiments/v3_ev_collab.py`: EV/TW/drone evaluator + greedy + experiment
- `src/results/v3_ev_collab_raw.csv` / `_summary.csv` / `_log.txt`
