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
  multi_takeoff=True` it reproduces the baseline solution under the same
  evaluator.
- Four configurations, anchored on V1 (truck-only EV, no drone):

  | Config | Customers per sortie | Stop reuse |
  |---|---:|---|
  | cap1 | 1 | allowed |
  | v2 | up to 2 | allowed |
  | notakeoff | up to 2 | not allowed (a stop serves one sortie) |
  | cap3 | up to 3 | allowed |

- Sizes 8/12/16/20, seeds 20260720-20260729 (ten), 40 instances.
- Every configuration optimises the same penalised objective the V3 greedy uses
  (makespan + 1000 x time-window violations), so makespan and violations are
  reported together.
- Self-check: with an empty sortie set the V3 evaluator matches the week-06
  truck-only EV route on makespan, violations and recharge count, 40/40.

## 3. Results

Means over ten seeds per size; the percentage is the makespan improvement over V1:

| Size | V1 (truck-only EV) | cap1 | v2 | notakeoff | cap3 |
|---|---:|---:|---:|---:|---:|
| N=8  | 485.8 | 353.2 (26.7%) | **293.6 (39.2%)** | 319.1 (34.2%) | 263.5 (45.7%) |
| N=12 | 694.7 | 576.9 (16.9%) | **517.4 (25.4%)** | 532.1 (23.3%) | 480.4 (31.2%) |
| N=16 | 975.9 | 799.8 (18.1%) | **693.9 (29.0%)** | 744.7 (23.7%) | 755.4 (22.3%) |
| N=20 | 1283.6 | 1037.9 (19.1%) | 1069.0 (16.3%) | 1095.1 (14.4%) | **1003.2 (21.6%)** |

Gain decomposition (percentage points of the improvement over V1):

| Size | Multi-customer (v2-cap1) | Stop reuse (v2-notakeoff) | cap3 (cap3-v2) |
|---|---:|---:|---:|
| N=8  | **+12.5** | +5.0 | +6.5 |
| N=12 | **+8.5** | +2.1 | +5.8 |
| N=16 | **+10.9** | +5.3 | −6.7 |
| N=20 | −2.8 | +1.9 | +5.3 |

Time-window violations (mean): V1 2.4 / 6.0 / 9.6 / 13.5 and v2 0.0 / 3.2 / 6.3 /
10.5; all four drone configurations are 100% energy-feasible.

Paired Wilcoxon over the 40 pairs (all sizes pooled; a negative mean difference
means the first is better):

| Comparison | n | Mean diff | p |
|---|---:|---:|---:|
| v2 vs cap1 (multi-customer) | 37 | −52.4 | 5.3×10⁻³ |
| v2 vs notakeoff (stop reuse) | 20 | −58.6 | 2.4×10⁻⁴ |
| cap3 vs v2 (cap3) | 38 | −18.8 | 0.139 (not significant) |

Figure: `figures/v3_ablation.png`.

## 4. What it says

1. **Multi-customer sorties are still the largest single gain under energy and
   time windows**: +12.5 / +8.5 / +10.9pp at N=8/12/16, and the pooled paired test
   is significant (p=5.3×10⁻³). At N=20 it turns to −2.8pp: the battery and the
   time windows squeeze the window in which a multi-customer sortie is worth
   taking, and on 20 customers the greedy no longer finds a stable combination.
2. **Stop reuse is a secondary factor**: +5.0 / +2.1 / +5.3 / +1.9pp
   (p=2.4×10⁻⁴). Only 20 of the 40 pairs are non-zero, i.e. on most instances
   allowing reuse and forbidding it give the same solution, so the switch only
   matters on some geometries.
3. **cap3 is not significant overall** (p=0.139) and is negative at N=16
   (−6.7pp): a three-customer sortie has to satisfy range, rendezvous and time
   windows together, which gets harder with a battery in the model.
4. All four drone configurations are 100% energy-feasible, and all of them have
   fewer time-window violations than V1.

Taken together, the three settings agree: multi-customer ability is the largest
single gain both in the FSTSP setting (synthetic +8.6 to +12.1pp, standard
instances +7.2 to +8.9pp) and under energy and time windows (+8.5 to +12.5pp). The
difference is where it runs out: under V3 it is gone by N=20, while the FSTSP
setting still shows +8.6pp there. The attribution holds under the stricter model,
but over a smaller range of instance sizes.

## 5. Limitations

- The four configurations share one greedy with a penalised acceptance rule, so
  part of the negative N=20 value is greedy myopia: a two-customer sortie locks up
  its launch and recovery stops and leaves no better combination afterwards.
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
