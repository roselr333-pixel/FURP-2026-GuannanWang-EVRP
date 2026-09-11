# Week 6 Integration Note (Track B: combine existing methods into one workflow)

> Student note. Written 2026-07-23 by Guannan Wang.
> This week's lab is titled *Integrate Methods and Explore Learning-Based Extensions*. I follow **Track B** — combining the pieces I already built into one reproducible workflow and validating one focused improvement. My focus throughout has been **ground-air collaborative EVRP-TW**. This note follows the four-section structure requested by the lab: Current Stage / Method Design / Experiment Plan / Preliminary Result.

## 1. Current Stage

Over the previous weeks I had built three fairly independent components:

- **W4 electric-vehicle constraints**: battery capacity, charging stations, and customer time windows, exercised through both OR-Tools and my own greedy routine.
- **W5 truck-drone modelling**: a drone that launches and lands at arbitrary truck nodes (FSTSP-style), with range and rendezvous constraints.
- **W1–W3 baselines**: OR-Tools on the 56 Solomon instances (mean gap 7.2%), plus a genetic-algorithm baseline I wrote myself.

The goal this week is not a new method, but to **integrate those separate scripts into one fair-comparison workflow** and validate one focused improvement inside it. The improvement I chose: take the W4 electric truck route and add the W5 drone coordination on top, and check whether it lowers the completion time without changing the solver.

Current status: V0 / V1 / V2 already share one constructive core and produce a stable "baseline vs. improvement" comparison; failure cases and all constraint metrics are reported. After adding the multi-seed experiment this week, the instance and seed counts now meet the lab's hard metrics (40 instances, 4 sizes, 10 seeds).

## 2. Method Design

### 2.1 Unified workflow

The whole pipeline is:

```
instance (random) → truck EV route (V1) → drone task allocation (V2) → evaluate (makespan / feasibility / violations)
```

The three variants differ only in which constraints are switched on; the constructive core is identical:

| Variant | What it models | Role |
|---|---|---|
| V0 | Truck-only, no battery limit | reference lower bound |
| V1 | Truck-only EVRP-TW (battery + charging + TW) | baseline |
| V2 | Ground-air collaborative EVRP-TW (V1 + drone) | proposed |

So any gap between V1 and V2 is purely the effect of adding the drone; the solver quality is the same, which keeps the comparison fair.

### 2.2 Truck EV route (the V1 core)

- Nearest-neighbour ordering with greedy sequential service of customers.
- Energy is consumed per distance (`RHO = 1.0`); when the battery is low the truck recharges to full at the nearest station (fixed `RECHARGE = 40`, a battery-swap assumption).
- Each customer has a `[e, l]` time window: early arrival waits, late arrival is recorded as a TW violation.

### 2.3 Drone task allocation (the V2 improvement)

The drone is carried by the truck, launched at truck node *i*, recovered at a later node *j*, and may serve several customers in between. A drone trip must satisfy three constraints:

1. **Range**: total flight length `i → (visited customers) → j` ≤ drone range `R_D = 160`;
2. **Rendezvous**: the drone lands at *j* no later than the truck arrives (it may wait, but cannot land after the truck has left);
3. **Time windows**: served customers meet their own windows. The drone battery resets on recovery.

**What changed vs. my previous version**: the earlier version offloaded only one customer per instance, so the collaborative benefit was small. This version allows up to **two customers per flight** and lets one truck stop be reused for several drone launches/recoveries.

**Heuristic**: starting from the V1 truck route, repeatedly scan every launch segment (i, j), enumerate the customer groups it could serve (single- and two-customer options), and accept a group only when removing those customers from the truck route lowers the truck makespan. Repeat until nothing more can be accepted. This keeps the drone busy while guaranteeing every offload actually helps the completion time.

### 2.4 Objective

Minimize makespan = max(truck completion time, drone completion time).

## 3. Experiment Plan

- **Instances**: randomly generated, 4 sizes N = {8, 12, 16, 20} customers, each with 4 charging stations. Locations, time windows, and demands are all fixed by seed, so runs are reproducible.
- **Seeds**: 10 random seeds per size (seed base `20260720`) = **40 instances**, meeting the lab's "≥10 instances + 3 sizes + multiple seeds" requirement.
- **Parameters**: truck speed `V_T = 1.0`, drone speed `V_D = 2.0`, drone range `R_D = 160`, battery `Q = 250`, recharge `RECHARGE = 40`, service `SERVICE = 10`, energy factor `RHO = 1.0`.
- **Reported metrics** (aligned with the project page's minimum standard): objective (makespan + total distance), feasibility, TW violations, energy/battery violations, recharge count and time, **synchronization violations** (drone trips rejected by the rendezvous rule), offloaded count, runtime, seed and parameters.
- **Failure cases**: 4 targeted instances (FC1–FC4) for constraint-level diagnosis, see §4.3.

## 4. Preliminary Result

### 4.1 Main comparison (mean over 40 instances)

| Size | V0 (ref. lower) | V1 (base) | V2 (prop.) | V2 vs V1 | mean offload | offload % | V2 feas. |
|---|---:|---:|---:|---:|---:|---:|---:|
| 8 | 434.7 | 485.8 | 240.5 | **−50.5%** | 5.2 / 8 | 65.0% | 100% |
| 12 | 614.4 | 694.7 | 312.2 | **−55.3%** | 8.5 / 12 | 70.8% | 100% |
| 16 | 816.6 | 975.9 | 448.3 | **−53.9%** | 11.5 / 16 | 71.9% | 100% |
| 20 | 1080.1 | 1283.6 | 741.9 | **−42.1%** | 13.4 / 20 | 67.0% | 100% |

- All 40 instances are feasible (V0 / V1 / V2 feasibility 100%).
- The mean V2-over-V1 improvement sits at **42%–55%**; the per-seed spread is 27.7%–71.7%, so the collaborative benefit is stable rather than a product of one lucky seed.
- Mean offload rate is 65%–72%: the drone serves the majority of customers in parallel across most instances.

### 4.2 How to read this

The gain comes from serving several customers with the faster drone **in parallel** with the truck, not from using fewer recharges (V1 and V2 have nearly identical recharge counts). V0 (no battery limit) has a slightly lower makespan than V1, which shows the battery/charging constraint does impose a real extra cost on the truck route — and V2 recovers part of that cost through the drone. This is what makes the ground-air collaborative line worth pursuing further.

### 4.3 Failure cases (constraint-level diagnosis)

| ID | Setting | What breaks | Note |
|---|---|---|---|
| FC1 | truck EV, recharge OFF, battery = 120 | energy violation (one full charge is not enough) | must allow recharge or raise battery |
| FC2 | collaborative, drone range = 40 (tiny) | only 2 offloaded, V2 ≈ V1 | too-small range makes the drone useless |
| FC3 | truck EV, tight TW (width = 35) | 10 customers outside window | tight windows break feasibility directly |
| FC4 | collaborative, 16 customers | 14822 trips rejected by rendezvous | the sync constraint is active and binding |

FC4 is worth a note: in the previous version, offloading only one customer per instance meant the rendezvous rule was almost never triggered. With multi-customer flights, the synchronization constraint becomes a genuine bottleneck — which in turn shows this "improvement" actually touches the problem's key constraint, rather than tinkering at the margins.

### 4.4 A note on learning-based extensions (Track C / D)

The lab also encourages exploring RL / DL. I have **not** switched to Track C / D, for practical reasons:

- My instances are still small (≤ 20 customers), whereas RL / DL usually need many samples and more realistic sizes to show value. On instances this small, an interpretable constructive heuristic already gives a clear, stable comparison.
- Track B first establishes the research workflow "variant → baseline → improvement → failure analysis", which is the lab's core goal; RL / DL can be layered on top of the existing baseline later (W7 / W8) rather than started from scratch now.

This is not to say learning methods are unimportant — only that, from the "build a reproducible workflow first" angle, doing Track B solidly is the better fit at this stage.

## 5. Limitations

- **Greedy, not optimized.** The route is nearest-neighbour + greedy insertion with no local search, so absolute numbers are far from optimal. The point is the fair comparison between variants, not the absolute value.
- **At most 2 customers per flight.** Enumeration is capped at single/two customers to keep runtime reasonable (two-customer is already O(n⁴)).
- **No literature reproduction yet.** This is my own heuristic; I have not yet reproduced Schneider (2014, E-VRPTW) or Murray & Chu (2015, FSTSP) as published baselines (P1 in my progress note is still pending).
- **Small instances.** 40 instances cover 4 sizes × 10 seeds, but are still 8–20 customers — enough to show the mechanism and stability, not enough for strong statistical claims or realistic road networks.

## 6. Next steps

1. Fold the data and conclusions of this note into the final report and the checkpoint.
2. Reproduce one paper method (Schneider 2014 or Murray & Chu 2015) and place it in the same comparison table, so my heuristic and a published method sit side by side.
3. Optionally raise the per-flight customer cap to 3 and optimize the enumeration, or scale up to 30+ customers to see the trend.

Files: `src/experiments/week06_ground_air_evrp_tw.py`, `src/results/week06_ground_air_results.csv` (40 raw rows), `src/results/week06_ground_air_summary.csv` (mean table per size), `src/results/week06_failure_cases.csv`.
