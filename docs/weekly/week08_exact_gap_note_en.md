# Exact optimality gap (CP-SAT, small instances)

## 1. Motivation

The evidence index has long carried one open item: "how far the heuristic is
from the optimum is not quantified". This section quantifies it by computing the
**exact optimum** of the collaborative problem on small instances with CP-SAT,
and reporting the gap of my greedy and of the LNS to that optimum.

## 2. A modelling issue that has to come first

The shared FSTSP evaluator (`week07_fstsp_repro.fstsp_simulate`) serialises
sorties with a `drone_avail` chain but never checks that the drone is back on the
truck. A sortie set that nests one sortie inside another (launch at 0, recover at
2, with a second sortie launched and recovered in between) is therefore given a
makespan even though one drone cannot fly two overlapping sorties.

Measured on the 15 instances at n=8/10/12, the project's original V2 produces
such an invalid plan in **14 of 15 cases** (1/5 valid at n=8, 0/5 at n≥10); with the main evaluator physical and everything re-run, the V2 plans are now valid on 15/15 instances. This
is the same class of defect as FC-7-2 / FC-7-3, on the FSTSP evaluator's code
path.

So both the optimum and the heuristics are defined on the **physical model**
(`cpsat_fstsp.py`):

- one serial drone; sorties do not overlap, a launch node must lie ahead of the
  truck and before the recovery node, and the drone must be on the truck at the
  launch node;
- each sortie serves 1-2 customers with total flight length at most `R_D`;
- the truck waits at a recovery node until the sortie lands.

## 3. Model and validation

**CP-SAT model** (`cpsat_fstsp.solve_exact`): the truck route uses arcs plus MTZ
positions; candidate sorties (launch/recover on truck nodes, 1-2 customers,
length ≤ `R_D`) are enumerated explicitly; time variables allow the truck to wait
(`t[j] ≥ t[i] + travel`, the slack being the waiting time); a launch/recovery
balance (a 0/1 "airborne when leaving each truck node" state) enforces the single
serial drone.

The model works in integer time units of `1/SC` with `SC = 100`, so every arc
and sortie flight is rounded to 0.01. A reconstructed plan therefore
re-evaluates to the objective only up to that discretisation (at most half a
step per arc and per sortie, about 0.03-0.05 on these instances); the self-test
compares against that bound rather than a fixed `1e-6`, which it used to do and
which failed whenever the optimum did not sit exactly on the grid.

**Warm start.** `solve_exact` takes two optional warm-start arguments:
`upper_bound` pins the objective at or below a known feasible makespan, and
`hint` feeds a known plan `(route, trips)` to CP-SAT with `AddHint` (route arcs,
MTZ positions, the truck/drone assignment and the selected sorties; the solver
completes the rest by propagation). The runner passes the better of the clean
greedy and the LNS plan to both, so the search starts from a feasible plan and only
has to prove optimality. The effect is real but not a guarantee: started cold at
n=12 the solver can return `UNKNOWN` with no solution at all inside the budget,
while the warm-started run reaches a feasible plan there; at n=14 one instance
still came back `UNKNOWN` in 60 s. What the warm start reliably changes is the
quantity the solver has to close -- the gap between its incumbent and the
relaxation.

**Two independent checks** (`tests/test_cpsat_exact.py`):

- setting the drone range to zero must reduce the model to a plain truck TSP —
  the result matches a Held-Karp exact TSP at n=6/7/8;
- an exhaustive enumeration of the whole physical solution space at n=5 (truck
  route plus recursive serial sorties) matches the CP-SAT optimum exactly.

One bug was found while modelling: writing the truck time as an equality
`t[j] = t[i] + travel` left no room for the truck to wait at a recovery node, so
every sortie that needed waiting was excluded and the optimum came out too high
(4-13% above the brute-force value at n=5). With an inequality both checks pass.

## 4. Results (5 seeds per size, n=8/10/12/14/16)

gap = (best plan CP-SAT found − heuristic) / that plan. At n=8 that plan is the
proven optimum; from n=10 on it is the best **feasible** plan found, so those gaps
are lower bounds on the true gap.

| size | optimum proved | feasible plan found | greedy gap (mean) | LNS gap (mean) | CP-SAT beats my best heuristic | dual bound non-trivial |
|---|---:|---:|---:|---:|---:|---:|
| n=8 | **5/5** | 5/5 | **31.2%** | **16.5%** | 13.4% | 5/5 |
| n=10 | 0/5 | 5/5 | 52.5% | 21.8% | 17.5% | 0/5 |
| n=12 | 0/5 | 5/5 | 44.7% | 20.1% | 16.3% | 0/5 |
| n=14 | 0/5 | 4/5 | 40.1% | 21.0% | 16.7% | 0/5 |
| n=16 | 0/5 | 4/5 | 30.4% | 9.8% | 8.8% | 0/5 |

Per-size budgets: 120 s at n=8, 60 s from n=10 on, 8 workers. "feasible plan
found" counts the instances where CP-SAT returned a plan at all inside the budget;
the gap means cover those instances. The original V2 plan is physically valid on
5/5 instances at every size (the FC-7 fix holds up to n=16).

## 5. What it shows and where it stops

1. **The warm start keeps the proven boundary and repairs the primal.** The n=8
   row is unchanged against the committed cold run — same five optima (158.49,
   204.21, 173.38, 211.88, 218.77), same 31.2% / 16.5% gaps — so the hint does not
   disturb the model; and where the cold search at n=12 could return `UNKNOWN` with
   no plan at all, the warm-started run returns a plan on 23 of 25 instances (4/5
   at n=14 and n=16).
2. **From n=10 on, the exact model is the better heuristic.** On the instances it
   solved, CP-SAT's plan is **8.8%–17.5% below the best plan my greedy and LNS
   found** (mean over sizes), so the earlier gap numbers were not an artefact of the
   proof: my LNS really is ~20% above a plan that a general-purpose model produces
   in a minute. That points at the search (a stronger metaheuristic) rather than at
   more exact-solver time — and the ALNS in `docs/weekly/week08_alns_note_en.md`
   takes that up: it takes 2.7–12.2% off the LNS and wins on some instances
   (n=14 seed 20260723), while the CP-SAT plan stays ahead on average.
3. **The boundary is on the dual side, not on the clock.** The certified lower
   bound is trivial at every size from n=10 on — `0.0` on all 20 instances — and a
   separate 300 s / 16-worker probe managed only 27.6 against an incumbent of 217
   at n=10 and 0 at n=12. Extra CP-SAT time therefore proves nothing there; the
   relaxation (one binary per candidate sortie plus the airborne-state chain) is
   what has to change, e.g. by a column-generation or Lagrangian bound over the
   sortie set.
4. **What the earlier numbers were.** The committed cold run (180 s per instance)
   reported n=10/12 LNS gaps of 26.4% / 23.5% against its own weaker incumbent;
   with the better incumbent the same heuristic is 21.8% / 20.1% away. The
   difference is the denominator, not the heuristic — worth keeping in mind when
   reading any unproved gap row.
5. **Caveats.** Unproved incumbents move between runs, so the n≥10 gap columns do
   too: at n=10 seed 20260724 the incumbent went from 252.2 (cold, 180 s) to 270.5
   (warm, 60 s) and the reported LNS gap moved from 16.6% to 8.7% on the same plan.
   The n=8 row is stable (proved), and the certified-gap column is only non-empty
   there. The n=8 gaps themselves still vary widely (0.04%–51.5%): on one instance
   the greedy happened to hit the optimum, on most it is far off.

## 5b. Correctness side-finding

The project's original V2/LNS plans were mostly not physically valid before the
evaluator fix; `fstsp_makespan_clean` and `clean_greedy` provide the clean
alternative and the validity column above tracks it. See FC-7-4 in
`docs/reference/failure_cases_master.md`.

## 6. Artifacts

- `src/experiments/cpsat_fstsp.py` — physical evaluator + clean greedy + CP-SAT exact model
- `src/experiments/week08_exact_gap.py` — runner
- `tests/test_cpsat_exact.py` — the two checks (plus optimum ≤ clean greedy)
- `src/results/week08_exact_gap_raw.csv` / `_summary.csv` / `_log.txt`
