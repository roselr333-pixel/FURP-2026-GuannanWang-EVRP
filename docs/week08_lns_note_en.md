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
| N=8  | 391.3 | 236.8 (−39.2%) | 235.0 | **213.1** (−45.5%) | **+9.70%** |
| N=12 | 579.4 | 359.3 (−37.8%) | 359.3 | **317.0** (−44.8%) | **+10.98%** |
| N=16 | 774.8 | 524.6 (−32.4%) | 514.3 | **462.2** (−40.2%) | **+10.95%** |
| N=20 | 1022.3 | 714.1 (−29.9%) | 706.7 | **624.5** (−38.5%) | **+11.56%** |
| N=30 | 1597.7 | 1212.7 (−24.4%) | 1201.2 | **1094.2** (−31.6%) | **+9.09%** |
| N=50 | 3114.1 | 2569.1 (−17.6%) | 2514.5 | **2233.1** (−28.1%) | **+12.56%** |

Parentheses give the makespan reduction vs truck-only (larger is better). Mean
per-instance runtime is 0.11–5.4 s (single machine, rising with size).

Figure: `figures/lns_vs_greedy.png` (left: completion time by size; right:
improvement over the greedy).

## 4. What it shows

- LNS improves the greedy V2 by a **consistent +9% to +12.6% at every size**,
  and this is not noise: a paired Wilcoxon signed-rank test gives an overall
  **p = 3.6×10⁻⁹**, with every individual size significant at the 0.05 level
  (see `stat_tests.csv`).
- LNS clearly **offsets the scaling decay**: the greedy's reduction vs truck-only
  falls from 39.2% (N=8) to 17.6% (N=50), while LNS only falls from 45.5% to
  28.1%. At N=50 the LNS still gives 28.1%, more than ten points above the greedy's
  17.6%.
- By contrast, an intra-route 2-opt on the truck backbone alone barely moves
  (0–2%). The gain therefore comes from **re-allocating drone tasks and the
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
