# W8 extension: standard instances + more drones + optimised scheduling

## 1. Motivation (three limitations at once)

The W8 multi-drone note left three limitations: (1) instances are random
geometry; (2) K only goes up to 3; (3) rendezvous/scheduling uses a simple
"earliest-available drone" rule, not an optimal schedule. This section handles
all three.

## 2. Standard instances (replacing random geometry)

- Use the coordinates of the **official Solomon instances** already in the repo
  (`src/instances/official_solomon/*.vrp`), taking the first n customers -- the
  usual FSTSP convention ("Solomon instance + a drone").
- Within these files, coordinates are shared per family, so there are **four
  distinct spatial topologies**: C101 (clustered), C201 (clustered-2), R101
  (uniform), RC101 (mixed).
- To keep the drone-range regime comparable with the earlier synthetic runs, the
  coordinates are translated (depot -> origin) and uniformly scaled so the
  customers' **RMS radius equals the synthetic generator's at the same n**; the
  model constants (truck/drone speed, service time, endurance R_D=160) are
  unchanged. So **only the spatial topology changes**.
- Sizes n = 10 / 20 / 30 / 50, i.e. 4 x 4 = 16 standard instances
  (deterministic, no random seed).

## 3. Drone count (K = 1/2/3/5)

Reduction vs truck-only (LNS solution):

| size | truck-only | K=1 | K=2 | K=3 | K=5 |
|---|---:|---:|---:|---:|---:|
| N=10 | 351.7 | 37.2% | 51.2% | 61.1% | **71.4%** |
| N=20 | 718.9 | 36.0% | 46.0% | 52.6% | **62.4%** |
| N=30 | 1218.0 | 33.5% | 43.9% | 51.5% | **57.5%** |
| N=50 | 2370.2 | 27.5% | 38.4% | 42.7% | **46.8%** |

On the **standard topologies** the conclusion matches the synthetic runs: more
drones give a higher benefit (46.8%~71.4% at K=5) and further flatten the
scaling-decay curve. By family, uniform-random R101 benefits most and clustered
C101 least -- as expected, dispersed customers suit the drone better.

> 2026-09-13: this table was re-run after the main evaluator was made physical
> (see `docs/analysis/evaluator_physical_fix_note_en.md`); the old N=10 K=1→5 was
> 36.7%→71.4% and N=50 was 23.3%→48.6%.

## 4. Drone scheduling: how far is the naive rule from optimal?

Treating the sortie-to-drone assignment as an explicit scheduling problem, three
methods share one simulation:

- **greedy**: each sortie goes to the earliest-available drone (the old rule);
- **local**: from greedy, repeatedly move a single sortie to another drone if it
  lowers the makespan;
- **optimal**: branch and bound for the exact minimum (sortie count <= 14; the
  cap rose from 12 to 14 after adding symmetry breaking);
- **lower bound (certificate)**: take the larger of two valid lower bounds -- (a)
  give every sortie its own drone (no contention at all), and (b) the total
  flight time divided by K (the minimum load bound for K drones). If the greedy
  schedule reaches it, the greedy assignment is provably optimal.

On the standard instances (64 (family, n, K) configs):

- the **local search gains 0.000% over greedy** -- it finds no improvement at all;
- **optimality certificate: on 64/64 configs greedy == the lower bound, so the
  naive rule is provably optimal on every config**;
- on the 32 configs with <= 14 sorties the naive rule matches the exact optimum
  (0.000%).

Conclusion: after the main evaluator was made physical the sortie sets no longer
overlap, so the K drones have **no contention** and the "earliest-available" rule
is **provably optimal on all 64 configs**. (Self-check: greedy equals the existing
`fstsp_makespan_multi` exactly, and greedy >= local >= optimal always holds.) The
earlier "31/64 + a small local gain" was a false contention created by nested
sorties.

Figure: `figures/multidrone_std.png` (left: benefit rising with K on standard
instances; right: the naive rule's gap to the optimum is near zero).

## 5. Limitations

- Time windows / energy: handled separately by V3 (electric truck + drone +
  charging + time windows), see `docs/weekly/v3_ev_collab_note_en.md`; this section
  still uses the FSTSP evaluator (no TW/energy).
- Original instances: added separately (the original Murray & Chu 2015 FSTSP
  set, 36 instances), see `docs/weekly/week08_mc_benchmark_note_en.md`; the standard
  instances here are still Solomon coordinates with a uniform rescale.
- Scheduling: provably optimal on about half the configs; with many sorties the
  lower bound is loose and optimality is not proven (see section 4).

## 6. Artifacts

- `src/experiments/fstsp_instances.py` -- Solomon standard-instance loader
- `src/experiments/drone_scheduling.py` -- greedy / local / optimal schedulers
- `src/experiments/week08_multidrone_std.py` -- standard-instance multi-drone
  (K=1/2/3/5) + scheduling comparison
- `src/results/week08_multidrone_std_raw.csv` / `_summary.csv`,
  `week08_scheduling.csv`, `week08_multidrone_std_log.txt`
- `src/tools/plot_multidrone_std.py` -> `figures/multidrone_std.png`
