# The original instances: Murray & Chu (2015) FSTSP benchmark

## 1. Motivation

The earlier "standard" instances were **Solomon coordinates with a uniform
rescale** (to keep the endurance scale), not the paper's original instance
files. This section switches to the **original Murray & Chu (2015) FSTSP
instances**.

## 2. Source

- Dataset: `Murray_Chu_2015_test_data`, publicly hosted by Dell'Amico,
  Montemanni & Novellani alongside their exact FSTSP models paper.
- Downloaded into `src/instances/murray_chu_2015/`: **36 instances with 10
  customers**, 11 of which ship an objective value (OFV) from the literature.
- Each instance has `nodes.csv` (coordinates + isTooHeavy), two time matrices
  `tau.csv` and `tauprime.csv`, `Cprime.csv` (customers the UAV may serve), and
  sometimes `FSTSP_OFV.csv`. Node 0 = starting depot, 1..c = customers,
  c+1 = ending depot.

## 3. Which matrix is the truck? Decided from the data

The bundled README does **not** say which of `tau` / `tauprime` belongs to which
vehicle, so it is calibrated from the data:

- Row 0, column 4 of `nodes.csv` is the **declared UAV speed** (0.2 / 0.4 / 0.6
  miles per minute, varying by instance).
- Both matrices are approximately proportional to the Euclidean distance, so
  each implies a speed. On **36 of 36 instances** the speed implied by
  `tauprime` matches the declared UAV speed (0.25 / 0.417 / 0.58 against
  0.2 / 0.4 / 0.6), while `tau` stays at about 0.33 across all instances.

=> **`tau` is the truck matrix and `tauprime` is the UAV matrix.**

A useful side effect: because the declared UAV speed varies, this benchmark
**spans "drone slower than the truck (0.2)" through "drone faster (0.6)"**, so
the collaboration benefit can be read against drone speed.

## 4. Results (36 instances, LNS, 200 iterations)

| config | LNS | vs truck-only TSP | LNS / literature OFV |
|---|---:|---:|---:|
| c1K1 (**exactly M&C's FSTSP**: one customer per sortie, one drone) | 50.86 | 22.3% | **0.924** |
| c1K2 | 44.77 | 31.7% | 0.795 |
| c1K3 | 41.11 | 37.2% | 0.692 |
| c2K1 (my multi-customer extension, up to 2 per sortie) | 49.60 | 24.4% | 0.900 |
| c2K2 | 42.83 | 34.7% | 0.734 |
| c2K3 | 40.56 | 38.2% | 0.678 |

("LNS / literature OFV" is averaged over the 11 instances that ship an OFV;
values below 1 mean better than the published objective.)

- **Under M&C's own FSTSP definition (one customer per sortie, one drone) my
  LNS reaches 0.924 of the published objective**, i.e. about 7.6% better than
  the objective values distributed with the instances.
- Multiple drones keep adding: 22.3% with one drone up to 37.2% with three
  (relative to the truck-only TSP).

## 5. Two things that must be stated

- **The instance files contain no drone endurance parameter**, so endurance is
  unlimited here, and the longest flight in each solution is reported: mean
  about 25-29 and a maximum of about 69 per configuration. If the literature applied
  an endurance limit, some long legs might not qualify.
- **The literature OFV comes from M&C's heuristics** (their MILP could not solve
  these 10-customer instances within 30 minutes), so "better than OFV" is
  relative to that heuristic value, not to a proven optimum.

## 6. Artifacts

- `src/instances/murray_chu_2015/`: the original instance files
- `src/experiments/fstsp_mc.py`: loader (with the tau/tauprime calibration),
  matrix-based evaluator, greedy and LNS
- `src/experiments/week08_mc_benchmark.py`: 36 instances x {c1,c2} x {K=1,2,3}
- `src/results/week08_mc_benchmark_raw.csv` / `_log.txt`
