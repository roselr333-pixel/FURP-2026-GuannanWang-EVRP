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
| N=10 | 351.7 | 36.7% | 53.4% | 63.1% | **71.4%** |
| N=20 | 718.9 | 30.9% | 44.1% | 48.6% | **60.1%** |
| N=30 | 1218.0 | 23.9% | 37.2% | 45.1% | **56.2%** |
| N=50 | 2370.2 | 23.3% | 34.7% | 41.8% | **48.6%** |

On the **standard topologies** the conclusion matches the synthetic runs: more
drones give a higher benefit (48.6%~71.4% at K=5) and further flatten the
scaling-decay curve. By family, uniform-random R101 benefits most (42.6% already
with a single drone at N=50) and clustered C101 least (23.3% at N=50) -- as
expected, dispersed customers suit the drone better.

## 4. Drone scheduling: how far is the naive rule from optimal?

Treating the sortie-to-drone assignment as an explicit scheduling problem, three
methods share one simulation:

- **greedy**: each sortie goes to the earliest-available drone (the old rule);
- **local**: from greedy, repeatedly move a single sortie to another drone if it
  lowers the makespan;
- **optimal**: branch and bound for the exact minimum (sortie count <= 14; the
  cap rose from 12 to 14 after adding symmetry breaking);
- **lower bound (certificate)**: give every sortie its own drone, i.e. no drone
  contention at all -- a valid lower bound on the optimum for any K. If the
  greedy schedule reaches it, the greedy assignment is provably optimal.

On the standard instances (64 (family, n, K) configs):

- the **local search gains only 0.001% on average over greedy (max 0.039%)**;
- **optimality certificate: on 31/64 configs greedy == the lower bound, so the
  naive rule is provably optimal there**;
- on the 43 configs with <= 14 sorties where the exact optimum is available, the
  **naive rule is on average only 0.196% above optimal (max 5.193%)**.

Conclusion: the "earliest-available" rule is **provably optimal on about half
the configs** and very close on the rest. **What is still open**: on configs
with many sorties the lower bound is loose, so the theoretical gain is bounded
only by mean 3.23% (max 40.08%) -- scheduling optimality at large multi-drone
scale is not proven. (Self-check: greedy equals the existing
`fstsp_makespan_multi` exactly, and greedy >= local >= optimal always holds.)

Figure: `figures/multidrone_std.png` (left: benefit rising with K on standard
instances; right: the naive rule's gap to the optimum is near zero).

## 5. Limitations

- Time windows / energy: handled separately by V3 (electric truck + drone +
  charging + time windows), see `docs/v3_ev_collab_note_en.md`; this section
  still uses the FSTSP evaluator (no TW/energy).
- Original instances: added separately (the original Murray & Chu 2015 FSTSP
  set, 36 instances), see `docs/week08_mc_benchmark_note_en.md`; the standard
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
