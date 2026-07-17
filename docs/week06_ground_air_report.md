# Week 6 — Ground-air Collaborative EVRP-TW (v2 iteration)

> Student note (low-key). Written 2026-07-17 by Guannan Wang.
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

## 4. Results (seed = 20260717, 4 instance sizes)

| Size | V1 makespan | V2 makespan | V2 vs V1 | TW viol (V1→V2) | recharges (V1/V2) | drone offload |
|---|---:|---:|---:|---:|---:|---:|
| 8 | 463.2 | 278.6 | **−39.9%** | 1 → 0 | 1 / 1 | 4 / 8 |
| 12 | 674.0 | 278.6 | **−58.7%** | 5 → 0 | 1 / 1 | 8 / 12 |
| 16 | 909.1 | 436.7 | **−52.0%** | 10 → 1 | 2 / 2 | 11 / 16 |
| 20 | 1221.5 | 704.4 | **−42.3%** | 14 → 2 | 3 / 3 | 14 / 20 |

Compared with the version that offloaded only one customer, the collaborative
benefit is now much larger:

- Previous version: V2 improved over V1 by only 12–21%, one customer offloaded.
- This version: V2 improved by 40–59%, with offload count rising with size
  (4 of 8 customers at size 8, up to 14 of 20 at size 20).

The improvement comes from serving several customers with the faster drone
**in parallel** with the truck, not from using fewer recharges (recharge
counts are identical). One coincidence worth noting: the 8- and 12-customer
instances happen to share a near-identical V2 makespan (~278.6) because both
truck sub-routes end at the same charging station before returning to the
depot, so the final leg takes the same time. This is an artifact of the
small seeded instances and does not affect the comparison.

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
- **Small instances.** 8 / 12 / 16 / 20 customers, single seed. Enough to
  show the mechanism, not enough for strong statistical claims.

## 8. What I would do next

1. Scale up instance sizes and add a few more random seeds for stability
   (currently only one seed).
2. Reproduce one paper method (Schneider 2014 or Murray & Chu 2015) and put
   it in the same comparison table.
3. Optionally raise the per-flight customer cap to 3 and optimize the
   enumeration.

Files: `src/experiments/week06_ground_air_evrp_tw.py`,
`src/results/week06_ground_air_results.csv`,
`src/results/week06_failure_cases.csv`,
`src/results/week06_ground_air_output.txt`.
