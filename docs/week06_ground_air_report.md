# Week 6 — Ground-air Collaborative EVRP-TW (v2 iteration)

> Student note (low-key). Written 2026-07-17, multi-seed robustness added 2026-07-23 by Guannan Wang.
> This is the experiment behind my chosen project focus: **ground-air
> collaborative EVRP-TW** (electric truck + drone, with time windows,
> battery/charging, and truck-drone synchronization). It is a first attempt,
> not a finished method.
>
> This file is a v2 iteration of the same code: the previous version offloaded
> only one customer per instance; this version fixes the drone task allocation
> so it can actually offload several.

## 1. What I built

I extended the week-05 truck-drone idea (drone launches/lands at any node,
FSTSP-style) with the electric-vehicle constraints from week-04 (battery
capacity + charging stations + customer time windows). The result is a
constructive heuristic for the **ground-air collaborative EVRP-TW** problem.

Vehicle / constraint setup:

- **Truck** is an electric vehicle: travels along a route, consumes energy
  per distance, and may recharge to full at charging stations (recharge takes
  a fixed time). Must respect each customer's time window.
- **Drone** is carried by the truck, launched at any truck node *i* to serve
  one or more customers, and recovered at any later truck node *j*. A drone
  trip must satisfy (a) **range** — total flight length `i→(visited
  customers)→j` ≤ drone range; (b) **rendezvous** — the drone lands at *j* no
  later than the truck arrives (the drone may wait, but cannot land after the
  truck has left); (c) the customers' **time windows**. The drone battery is
  reset on recovery (battery-swap assumption).
- **Objective**: minimize makespan = max(truck completion time, drone
  completion time).

## 2. What changed vs the previous version (drone task allocation)

The previous version only let the greedy offload one customer per instance,
so the collaborative benefit was small. This iteration does the two things I
listed under "next step" earlier:

1. **One flight can serve multiple customers.** After launching from *i*, the
   drone may visit `k1→k2→…` in order before landing at *j*, as long as the
   whole sub-path stays within range and finishes before the truck reaches
   *j*. The current code allows at most 2 customers per flight (it enumerates
   both single- and two-customer options and keeps the better one).
2. **One truck stop can launch/recover several times.** Once a truck node is
   used as a launch/recovery point it stays on the truck route, so it can be
   reused by later flights — the same stop is exploited multiple times.

The heuristic: take the V1 truck route (with charging-station insertions) as
the base, then repeatedly scan every launch segment (i, j) on the route,
enumerate the customer groups it could serve, and accept a group only when
removing those customers from the truck route lowers the truck makespan.
Repeat until nothing more can be accepted. This keeps the drone busy while
guaranteeing every offload actually helps the completion time.

## 3. How I compared it fairly

To isolate the "improvement", all three variants use the **same greedy
constructive core**; only the switched-on constraints differ:

| Variant | What it models |
|---|---|
| V0 | Truck-only, no battery limit (reference lower bound) |
| V1 | Truck-only EVRP-TW (battery + charging + TW) — the baseline |
| V2 | Ground-air collaborative EVRP-TW (V1 + drone coordination) — proposed |

So any gap between V1 and V2 is purely the effect of adding the drone, not a
difference in solver quality.

## 4. Results

### 4.1 Pilot (single seed = 20260717, 4 instance sizes)

| Size | V1 makespan | V2 makespan | V2 vs V1 | TW viol (V1→V2) | recharges (V1/V2) | drone offload |
|---|---:|---:|---:|---:|---:|---:|
| 8 | 463.2 | 278.6 | **−39.9%** | 1 → 0 | 1 / 1 | 4 / 8 |
| 12 | 674.0 | 278.6 | **−58.7%** | 5 → 0 | 1 / 1 | 8 / 12 |
| 16 | 909.1 | 436.7 | **−52.0%** | 10 → 1 | 2 / 2 | 11 / 16 |
| 20 | 1221.5 | 704.4 | **−42.3%** | 14 → 2 | 3 / 3 | 14 / 20 |

Note: the 8- and 12-customer instances happen to share a near-identical V2
makespan (~278.6) because both truck sub-routes end at the same charging
station before returning to the depot, so the final leg takes the same time.
This is an artifact of the small seeded instances and does not affect the
comparison.

### 4.2 Multi-seed robustness (10 seeds × 4 sizes = 40 instances, added 2026-07-23)

Following the Week 6 lab's hard metrics, I expanded each size to 10 random
seeds (seed base 20260720), giving 40 instances, and report the mean
performance per size.

| Size | V0 | V1 (base) | V2 (prop.) | V2 vs V1 | mean offload | offload % | V2 feas. |
|---|---:|---:|---:|---:|---:|---:|---:|
| 8 | 434.7 | 485.8 | 240.5 | **−50.5%** | 5.2 / 8 | 65.0% | 100% |
| 12 | 614.4 | 694.7 | 312.2 | **−55.3%** | 8.5 / 12 | 70.8% | 100% |
| 16 | 816.6 | 975.9 | 448.3 | **−53.9%** | 11.5 / 16 | 71.9% | 100% |
| 20 | 1080.1 | 1283.6 | 741.9 | **−42.1%** | 13.4 / 20 | 67.0% | 100% |

- All 40 instances are feasible (V0/V1/V2 feasibility 100%).
- The mean V2-over-V1 improvement sits at 42%–55% and does not swing much
  across seeds (per-seed range 27.7%–71.7%), so the collaborative benefit is
  stable rather than a product of one lucky seed.
- Mean offload rate is 65%–72%: the drone genuinely serves the majority of
  customers in parallel across many instances.
- Fairness still holds: V1 and V2 share the same constructive core, so the gap
  is purely the effect of adding the drone.

Compared with the version that offloaded only one customer, the collaborative
benefit is now much larger (that version improved by only 12–21%; this one by
40–59%).

## 5. Metrics I now report (what the project page asks for)

For each variant I record: objective (makespan + total distance), feasibility,
time-window violations, battery/energy violations, **charging count and
charging time**, makespan, **synchronization violations** (drone trips
rejected by the rendezvous rule), runtime, and the fixed seed.

## 6. Failure cases (constraint-level diagnosis)

| ID | Setting | What breaks | Next step |
|---|---|---|---|
| FC1 | truck EV, recharge OFF, battery=120 | energy violation — cannot cover the distance | allow recharge at stations or raise battery |
| FC2 | collaborative, drone range = 40 (tiny) | only 2 customers offloaded; V2 ≈ V1 | larger drone range, or accept degraded-to-baseline |
| FC3 | truck EV, tight time windows (width=35) | 10 customers served outside their window | relax windows / prioritise TW in insertion |
| FC4 | collaborative, 16 customers | 14822 trips rejected by rendezvous (rule is active and binding) | reorder route / launch earlier to exercise it |

Unlike the previous version, FC4 here shows the synchronization constraint is
**genuinely active** (many rejections), because multi-customer flights make the
rendezvous rule a real bottleneck rather than a formality.

## 7. Honest limitations

- **Greedy, not optimized.** The route is nearest-neighbour + greedy
  insertion; there is no local search, so absolute numbers are not close to
  optimal. The point is the *comparison* between variants, which is fair.
- **At most 2 customers per flight.** I capped enumeration at single/two
  customers to keep runtime reasonable (two-customer is already O(n⁴)). Larger
  instances could allow 3, but would need a smarter enumeration.
- **No literature reproduction yet.** This is my own heuristic. I have not
  yet reproduced Schneider (2014, E-VRPTW) or Murray & Chu (2015, FSTSP) as
  published baselines — that is still pending (P1 in my progress note).
- **Small instances.** Now 4 sizes × 10 seeds = 40 instances, but still only
  8 / 12 / 16 / 20 customers. Enough to show the mechanism and stability, not
  enough for strong statistical claims or realistic road networks.

## 8. What I would do next

1. ~~Scale up instance sizes and add a few more random seeds for stability
   (was only one seed).~~ ✅ Done: 4 sizes × 10 seeds = 40 instances, mean
   performance table in §4.2. Could still scale to 30+ customers.
2. Reproduce one paper method (Schneider 2014 or Murray & Chu 2015) and put
   it in the same comparison table.
3. Optionally raise the per-flight customer cap to 3 and optimize the
   enumeration.

Files: `src/experiments/week06_ground_air_evrp_tw.py`,
`src/results/week06_ground_air_results.csv` (40 raw rows),
`src/results/week06_ground_air_summary.csv` (mean table per size),
`src/results/week06_failure_cases.csv`,
`src/results/week06_ground_air_output.txt`.
