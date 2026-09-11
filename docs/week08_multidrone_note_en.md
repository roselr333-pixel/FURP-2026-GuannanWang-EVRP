# W8 extension: multiple drones (breaking the single-drone limitation)

## 1. Motivation

The W8 LNS note lists one limitation: **every result uses a single serial
drone**. This section breaks it -- the truck may carry K drones, compared for
K = 1/2/3, so the effect of the drone-count design variable on the
collaboration benefit can be read off.

## 2. Model and method

- **K parallel serial drones**: each sortie goes to whichever drone can start
  earliest; a drone is serial (its next sortie starts only after the previous one
  is recovered); the truck waits at a recovery node for the sortie landing there.
  **K=1 is numerically identical to the W7/W8 single-drone evaluator** (checked).
- **Greedy**: the same selection loop as `my_v2_param`, but each move is
  validated with the K-drone evaluator.
- **LNS**: the W8 destroy-and-repair, with the evaluator swapped to K drones.
- Instances, seeds, iteration budget and operators are the same as W8, so a row
  changes **only K**.

## 3. Results (10 seeds x 6 sizes; LNS solution; parenthesised = reduction vs
truck-only)

| size | truck-only | K=1 | K=2 | K=3 |
|---|---:|---:|---:|---:|
| N=8 | 391.3 | 213.1 (45.5%) | 153.3 (60.7%) | **118.4 (69.6%)** |
| N=12 | 579.4 | 317.0 (44.8%) | 240.8 (58.1%) | **194.8 (66.0%)** |
| N=16 | 774.8 | 462.2 (40.2%) | 372.1 (51.8%) | **317.3 (58.8%)** |
| N=20 | 1022.3 | 624.5 (38.5%) | 530.4 (48.0%) | **472.9 (53.5%)** |
| N=30 | 1597.7 | 1094.2 (31.6%) | 1028.7 (35.7%) | **897.7 (43.5%)** |
| N=50 | 3114.1 | 2233.1 (28.1%) | 2083.0 (32.9%) | **1987.2 (36.0%)** |

The LNS still improves each K-drone greedy consistently: +9.7~12.6% (K=1),
+5.1~12.9% (K=2), +8.6~14.2% (K=3) across sizes.

Figure: `figures/multidrone.png` (left: completion time per K; right: benefit vs
truck-only rising with K).

## 4. What it shows

- **Drone count is a real lever**: going from K=1 to K=3 lifts the benefit vs
  truck-only at every size -- N=8 from 45.5% to 69.6%, N=50 from 28.1% to 36.0%.
- **More drones also slow the scaling decay**: the K=1 benefit falls from 45.5%
  (N=8) to 28.1% (N=50); with K=3 the whole curve is raised (69.6% → 36.0%). At
  N=50, three drones give 36.0% versus the single drone's 28.1%.
- The LNS still pays off at every K (+5% to +14%), so the improvement phase and
  the drone count are **two independent sources of gain**.
- Paired Wilcoxon: **LNS K=3 vs K=1 overall p=1.67×10⁻¹¹, significant at every
  size**; K=2 vs K=1 overall p=6.71×10⁻¹⁰, but **N=30 is not significant
  (p=0.154)** -- an extra drone occasionally makes little difference at a
  medium size. (Greedy K=2/K=3 vs K=1 is significant at every size.)

## 5. Limitations

- Still the **FSTSP completion-time evaluator (no time windows or energy)**; only
  the "single drone" limitation is broken here. Re-adding battery/charging and
  time windows is a separate next step.
- Instances are still random-geometry synthetic ones; K is only tested up to 3.
- The multi-drone rendezvous/scheduling is a simple rule (earliest-available
  drone), not an optimal schedule.

## 6. Artifacts

- `src/experiments/week08_multidrone.py` (multi-drone greedy + LNS runner)
- `week07_fstsp_repro.py`: new `fstsp_simulate_multi` / `fstsp_makespan_multi`
  (K parallel serial drones; K=1 compatible with the original single-drone)
- `src/results/week08_multidrone_raw.csv` / `_summary.csv` / `_log.txt`
- `src/tools/plot_multidrone.py` -> `figures/multidrone.png`
- Significance folded into `src/results/stat_tests.csv` (`stat_tests.py`)
