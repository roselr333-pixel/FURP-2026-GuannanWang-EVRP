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

**Two independent checks** (`tests/test_cpsat_exact.py`):

- setting the drone range to zero must reduce the model to a plain truck TSP —
  the result matches a Held-Karp exact TSP at n=6/7/8;
- an exhaustive enumeration of the whole physical solution space at n=5 (truck
  route plus recursive serial sorties) matches the CP-SAT optimum exactly.

One bug was found while modelling: writing the truck time as an equality
`t[j] = t[i] + travel` left no room for the truck to wait at a recovery node, so
every sortie that needed waiting was excluded and the optimum came out too high
(4-13% above the brute-force value at n=5). With an inequality both checks pass.

## 4. Results (5 seeds per size, n=8/10/12)

gap = (heuristic − optimum) / optimum.

| size | optimality proven | greedy gap (mean) | LNS gap (mean) | greedy range | LNS range | original V2 plan valid |
|---|---:|---:|---:|---:|---:|---:|
| n=8 | **5/5** | **31.2%** | **16.5%** | 0.04 – 51.5% | 0.04 – 30.8% | 5/5 |
| n=10 | 0/5 | 58.0% | 26.4% | 43.4 – 78.6% | 16.6 – 45.7% | 5/5 |
| n=12 | 0/5 | 49.1% | 23.5% | 31.2 – 69.9% | 14.3 – 32.1% | 5/5 |

## 5. What it shows and where it stops

- **The "optimality is not quantified" item is now closed.** On small instances
  my greedy is about 31% above the optimum (n=8, proven) and above 50% at larger
  sizes; **the LNS roughly halves the gap** (16.5% / 25-27%), which quantifies the
  value of the improvement phase for the first time.
- Limits: at n≥10 the optimum was **not proved within 180s**, so the value
  reported is an **upper bound** on the optimum and the gap there is a **lower
  bound** on the true gap — the real gap is at least as large. CP-SAT still cannot
  prove optimality at n≥12; the model is weak in the number of candidate sorties
  and in the time relaxation, which is the natural next improvement.
- The n=8 gaps vary widely (0.04% to 51.5%): on one instance the greedy happened
  to hit the optimum, on most it is far off. This matches the qualitative point
  that the greedy has no improvement phase.
- A correctness side-finding: the project's original V2/LNS plans are mostly not
  physically valid. Reporting feasible solutions requires a physical-feasibility
  constraint; `fstsp_makespan_clean` and `clean_greedy` provide a clean alternative.

## 6. Artifacts

- `src/experiments/cpsat_fstsp.py` — physical evaluator + clean greedy + CP-SAT exact model
- `src/experiments/week08_exact_gap.py` — runner
- `tests/test_cpsat_exact.py` — the two checks (plus optimum ≤ clean greedy)
- `src/results/week08_exact_gap_raw.csv` / `_summary.csv` / `_log.txt`
