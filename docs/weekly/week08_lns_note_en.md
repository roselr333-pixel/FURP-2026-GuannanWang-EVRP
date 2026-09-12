# W8 supplementary experiment: an LNS improvement phase for the truck-drone heuristic

## 1. Motivation

My V2 is a constructive greedy: from a nearest-neighbour truck route it repeatedly
offloads the best drone sortie it can find until no single sortie improves the
makespan. It has no improvement phase, so its result is a local optimum of that
insertion order. The scaling study (`week06_largeN`) shows the collaborative gain
collapsing as N grows, which is what a greedy without an improvement operator
looks like.

This step adds a **destroy-and-repair LNS** on top of the same V2 solution and
measures how much it helps. The evaluator is still the W7 FSTSP completion time
(single serial drone, rendezvous enforced), so the comparison against the greedy
V2 and the published baseline stays apples-to-apples.

## 2. Method

- **State**: `route` (truck backbone; drone-served customers are not in it) plus
  `drone_trips`, each `(launch_node, customer_tuple, recover_node)`.
- **Destroy**: remove q customers -- random / the q largest truck-removal
  savings / a whole drone sortie.
- **Repair**: re-insert every removed customer by the cheapest option: (a) the
  best truck-route position, (b) a single-customer sortie, (c) paired with another
  pending customer in one sortie. Launch/recover nodes are only enumerated among
  the nearest route nodes to the customer.
- **Accept**: simulated annealing (accept a worse solution with `exp(-Δ/T)`),
  keeping the best solution seen.
- **Determinism**: one RNG per instance derived from the instance seed, with a
  fixed iteration budget (8:300 / 12:300 / 16:300 / 20:400 / 30:250 / 50:150);
  a re-run with the same seed reproduces the same numbers.

## 3. Results

10 seeds x 6 sizes (N=8/12/16/20/30/50) = 60 instances, one shared evaluator:

| size | truck-only | V2 greedy | greedy+2-opt | greedy+LNS | LNS vs greedy |
|---|---:|---:|---:|---:|---:|
| N=8  | 391.3 | 256.0 (−34.5%) | 247.7 | **222.2** (−43.2%) | **+12.51%** |
| N=12 | 579.4 | 412.1 (−28.9%) | 400.2 | **338.5** (−41.6%) | **+16.78%** |
| N=16 | 774.8 | 554.4 (−28.4%) | 533.9 | **471.0** (−39.2%) | **+13.29%** |
| N=20 | 1022.3 | 767.2 (−25.0%) | 746.3 | **594.4** (−41.9%) | **+21.32%** |
| N=30 | 1597.7 | 1270.1 (−20.5%) | 1220.6 | **1037.4** (−35.1%) | **+16.91%** |
| N=50 | 3114.1 | 2641.3 (−15.2%) | 2588.4 | **2188.4** (−29.7%) | **+16.59%** |

Parentheses give the makespan reduction vs truck-only (larger is better). Mean
per-instance runtime is 0.15–6.1 s (single machine, rising with size).

> 2026-09-13: this table was re-run after the main evaluator was made physical
> (see `docs/analysis/evaluator_physical_fix_note_en.md`); the old figures were
> +9%~+12.6% for LNS over greedy.

Figure: `figures/lns_vs_greedy.png` (left: completion time by size; right:
improvement over the greedy).

## 4. What it shows

- LNS improves the greedy V2 by a **consistent +12.5% to +21.3% at every size**,
  and this is not noise: a paired Wilcoxon signed-rank test gives an overall
  **p = 1.7×10⁻¹⁰**, with every individual size significant at the 0.05 level
  (see `stat_tests.csv`).
- LNS clearly **offsets the scaling decay**: the greedy's reduction vs truck-only
  falls from 34.5% (N=8) to 15.2% (N=50), while LNS only falls from 43.1% to
  29.5%; at N=50 the LNS still gives 29.5%.
- By contrast, an intra-route 2-opt on the truck backbone alone adds only about
  2%~3.2%. The gain therefore comes mainly from **re-allocating drone tasks and the
  overall structure**, not from route polishing -- consistent with the W7 ablation
  finding that multi-customer ability is the main gain.
- The earlier "greedy has no local search" limitation now has an actual
  improvement operator (LNS) behind it, rather than only a future-work note.

## 5. Limitations

- Still a **single drone** with the FSTSP completion-time evaluator (no time
  windows or energy); the LNS gain is measured under that setting.
- Instances are still random-geometry synthetic ones; the field's standard FSTSP
  instance sets are not used. N=100 is not tested (one LNS run already costs about
  5 s, so larger sizes need candidate pruning or parallelism first).
- The LNS parameters (iterations, destroy size, annealing schedule) are one fixed
  choice, not a sensitivity sweep.

## 6. Artifacts

- `src/experiments/week08_lns.py` -- LNS implementation and experiment runner
- `src/results/week08_lns_raw.csv` / `_summary.csv` / `_log.txt`
- `src/experiments/stat_tests.py` -- paired Wilcoxon test (numpy, no new dependency)
- `src/results/stat_tests.csv` / `stat_tests_log.txt`
- `src/tools/plot_lns.py` -> `figures/lns_vs_greedy.png`
