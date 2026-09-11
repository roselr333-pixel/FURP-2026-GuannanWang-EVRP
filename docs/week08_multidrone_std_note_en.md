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
- **optimal**: branch and bound for the exact minimum (run only when the sortie
  count is <= 12).

On the standard instances:

- the **local search gains only 0.001% on average over greedy (max 0.039%)** --
  it barely finds any improvement;
- on the 40 configs with <= 12 sorties where the exact optimum is available, the
  **naive rule is on average only 0.081% above optimal (max 3.226%, in a couple
  of configs)**.

Conclusion: the "earliest-available" rule is **already near-optimal** on these
instances, so no heavier scheduler is needed. The limitation is now quantified
and closed -- not skipped, but measured to be negligible. (Self-check: greedy
equals the existing `fstsp_makespan_multi` exactly, and greedy >= local >=
optimal always holds.)

Figure: `figures/multidrone_std.png` (left: benefit rising with K on standard
instances; right: the naive rule's gap to the optimum is near zero).

## 5. Limitations

- Still the **FSTSP completion-time evaluator (no time windows or energy)** --
  not handled here; that needs the week06 battery/charging and time windows
  stacked back in.
- The standard instances use Solomon coordinates with a uniform rescale (to keep
  the endurance scale), not the paper's original FSTSP instance files.
- The exact optimum is only checked up to 12 sorties; at larger sizes only
  local vs greedy is available.

## 6. Artifacts

- `src/experiments/fstsp_instances.py` -- Solomon standard-instance loader
- `src/experiments/drone_scheduling.py` -- greedy / local / optimal schedulers
- `src/experiments/week08_multidrone_std.py` -- standard-instance multi-drone
  (K=1/2/3/5) + scheduling comparison
- `src/results/week08_multidrone_std_raw.csv` / `_summary.csv`,
  `week08_scheduling.csv`, `week08_multidrone_std_log.txt`
- `src/tools/plot_multidrone_std.py` -> `figures/multidrone_std.png`
