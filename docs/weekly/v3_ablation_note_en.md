# Core ablation on the V3 model (electric truck + drone + charging + time windows)

> Written 2026-09-13. This completes the third setting for the core ablation.
> The week-07 ablation runs on the FSTSP evaluator (unlimited truck range, no time
> windows) and week07_ablation_std moves it to standard Solomon topologies, but
> neither has a battery or time windows. V3 is the setting that actually matches
> EVRP-TW, so the same decomposition is repeated here.

## 1. Why

In the FSTSP setting the truck's only limit is distance. In V3 the truck has a
battery, must detour to recharge when the charge is short, and customers have time
windows. Whether "multi-customer sorties are the main gain source" still holds
under energy and time windows has to be checked separately: a battery changes
what offloading a customer is worth, and time windows punish any arrangement that
makes the truck late.

## 2. How

- I reused `v3_ev_collab.v3_greedy` and added only two switches: `max_cust`
  (customers per sortie, 1/2/3) and `multi_takeoff` (may one truck stop serve
  several sorties). Both are behaviour-preserving: with `max_cust=2,
  multi_takeoff=True` it reproduces the committed `v3_ev_collab.py` results
  instance by instance (240.5 / 374.4 / 815.0 / 1051.8 at n=8/12/16/20, seed
  20260720).
- Four configurations, anchored on V1 (truck-only EV, no drone):

  | Config | Customers per sortie | Stop reuse |
  |---|---:|---|
  | cap1 | 1 | allowed |
  | v2 | up to 2 | allowed |
  | notakeoff | up to 2 | not allowed (a stop serves one sortie) |
  | cap3 | up to 3 | allowed |

- Sizes 8/12/16/20, seeds 20260720-20260729 (ten), 40 instances, the same seeds
  as `v3_ev_collab.py`.
- Every configuration optimises the same penalised objective the V3 greedy uses
  (makespan + 1000 x time-window violations), so makespan and violations are
  reported together.
- Self-check: with an empty sortie set the V3 evaluator matches the week-06
  truck-only EV route on makespan, violations and recharge count, 40/40.

## 3. Results

Means over ten seeds per size; the percentage is the makespan improvement over V1:

| Size | V1 (truck-only EV) | cap1 | v2 | notakeoff | cap3 |
|---|---:|---:|---:|---:|---:|
| N=8  | 485.8 | 338.1 (30.0%) | **257.8 (46.4%)** | 312.9 (35.4%) | 224.4 (53.6%) |
| N=12 | 694.7 | 550.9 (20.7%) | **415.1 (40.1%)** | 515.2 (26.1%) | 370.7 (46.4%) |
| N=16 | 975.9 | 719.8 (26.1%) | **628.7 (35.6%)** | 724.0 (25.9%) | 679.3 (30.2%) |
| N=20 | 1283.6 | 944.6 (26.2%) | **918.9 (27.9%)** | 1084.8 (15.2%) | 884.6 (30.7%) |

Gain decomposition (percentage points of the improvement over V1):

| Size | Multi-customer (v2-cap1) | Stop reuse (v2-notakeoff) | cap3 (cap3-v2) |
|---|---:|---:|---:|
| N=8  | **+16.4** | +11.0 | +7.2 |
| N=12 | **+19.4** | +14.0 | +6.3 |
| N=16 | +9.5 | +9.7 | −5.4 |
| N=20 | +1.7 | **+12.7** | +2.8 |

Time-window violations (mean): V1 2.4 / 6.0 / 9.6 / 13.5 and v2 0.0 / 1.9 / 6.0 /
9.7; all four drone configurations are 100% energy-feasible.

Paired Wilcoxon over the 40 pairs (all sizes pooled; a negative mean difference
means the first is better):

| Comparison | n | Mean diff | p |
|---|---:|---:|---:|
| v2 vs cap1 (multi-customer) | 40 | −83.2 | 9.4×10⁻⁵ |
| v2 vs notakeoff (stop reuse) | 39 | −106.8 | 5.5×10⁻⁸ |
| cap3 vs v2 (cap3) | 40 | −15.4 | 0.105 (not significant) |

Figure: `figures/v3_ablation.png`.

## 4. What it says

1. **Multi-customer sorties are still the largest single gain, but only at small
   and medium scale**: +16.4/+19.4pp at N=8/12, +9.5pp at N=16, and only +1.7pp
   at N=20. The pooled paired test is still significant (p=9.4×10⁻⁵).
2. **Stop reuse stops being a secondary factor under V3**: +11.0/+14.0/+9.7/+12.7pp
   (p=5.5×10⁻⁸), and from N=16 upwards it matches or beats the multi-customer
   ability (at N=20, +12.7pp against +1.7pp). That is clearly different from the
   FSTSP setting, where multiple take-offs contributed only +2.2 to +4.4pp.
3. **cap3 is not significant overall** (p=0.105) and is even negative at N=16
   (−5.4pp).
4. All four drone configurations are 100% energy-feasible, and all of them have
   fewer time-window violations than V1.

The mechanism that fits: the V3 truck detours to recharge and must satisfy time
windows, so binding two customers into one take-off saves a stop but makes the
rendezvous timing more fragile, while reusing one truck stop for several sorties
offloads customers without changing the shape of the truck route. In other words,
**the attribution depends on the model setting**: under the pure-distance FSTSP
setting multi-customer sorties dominate, and under EVRP-TW they matter about as
much as stop reuse. That is worth stating in the report rather than quoting the
FSTSP numbers alone.

## 5. Limitations

- The four configurations share one greedy with a penalised acceptance rule, so
  part of the cap3 result is greedy myopia: a three-customer sortie locks up its
  launch and recovery stops and leaves no better combination afterwards.
- Time windows are still a penalty rather than a hard constraint (the model is
  documented in `docs/reference/formal_model_en.md`).
- Single drone only; the K>1 case is in `docs/weekly/v3_ev_collab_note_en.md`.
- Sizes stop at N=20.

---

*Data provenance:*
- `src/results/v3_ablation_raw.csv` / `_summary.csv` / `_stat_tests.csv` (40 instances x 4 configs)
- `src/experiments/v3_ablation.py` (runner), `src/experiments/v3_ev_collab.py` (reused greedy and evaluator)
- `src/experiments/stat_tests.py` (paired Wilcoxon)
- `src/tools/gen_v3_ablation_figure.py` -> `figures/v3_ablation.png`
