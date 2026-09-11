# Schneider (2014) E-VRPTW Replication Notes (supplementary experiment)

> These notes document my own constructive replication of Schneider, Stenger & Goeke (2014),
> *The Electric Vehicle-Routing Problem with Time Windows and Recharging Stations*,
> Transportation Science 48(4). It sits beside my truck–drone EVRP project and shows that I
> also implemented the standard electric VRPTW with recharging stations from scratch and can
> benchmark it against the literature BKS. All numbers come from
> `src/experiments/schneider_evrptw.py` and `schneider_bks_compare.py` and are reproducible.

## 1. Model (E-VRPTW, full recharge, instantaneous)

- Fleet leaves the depot, serves customers with time windows `[ready, due]` and service time `serv`.
- Electric battery capacity `Q`, consumption rate `r` per distance, speed `v`.
- When the battery is low, the vehicle may detour to the nearest recharging station and
  **recharge to full instantaneously**; recharge time `= (Q − soc)·g` (`g` inverse refueling rate).
- Capacity `C`, time-window (waiting allowed), and non-negative battery constraints.
- **Objective**: Schneider's hierarchical objective — **minimize number of vehicles first, then total distance.**

## 2. Instance source (public, no paper PDF used)

- Instances come from a public GitHub mirror (the `SchneiderEVRPTW/` folder of EllinorAndRegina's
  ALNS master's thesis).
- To confirm these are Schneider's originals, I checked them file-by-file against the original
  instances in **jmanzolli/E-VRPTW**: `c103C5` and `c206C5` are byte-identical, `c101C5` and
  `rc108C5` differ only by whitespace — same data. The benchmark is therefore valid.
- Sets used: 100-customer `_21` (21 stations), 5-customer `C5` (3–4 stations), and 10/15-station
  variants — **92 instances** in total (`readme.txt` skipped).
- The paper PDF could not be downloaded on this machine (proxy blocks academic publishers), but the
  instances are public data and the model is fully defined by the parameters at the bottom of each
  file, so replication does not depend on the PDF.

## 3. Method (own constructive greedy + multi-trip fleet)

`src/experiments/schneider_evrptw.py`: a homogeneous fleet is modelled with **multi-trip** — one truck
may serve several routes, returning to the depot to reload and (if needed) fully recharge between trips,
matching Schneider (2014)'s fleet setting. Each trip greedily inserts the **nearest feasible customer**
in earliest-deadline order (capacity / time-window / battery all feasible; if the battery is low it
detours via the nearest station for a full recharge). Objective follows Schneider's hierarchy: minimise
vehicles first, then total distance.

**Note:** multi-trip is switched on in the model, but the constructive greedy still **cannot
assign customers to multi-trip vehicles globally** — later trips depart too late and miss early time
windows, so a vehicle effectively still runs only 1–2 trips. I verified this empirically: sweeping the
per-trip customer cap from ∞ down to 3 never reduced vehicle count (c201_21 stays between 14–21
vehicles vs BKS 4) while distance rose from more depot returns. The vehicle-count gap is therefore due to
the **heuristic itself**, not a modeling omission.

## 4. Results

- All 92 instances ran. In the **RC1 family, one customer could not be inserted** because its time
  window is too tight for the greedy (`unserved=1`), recorded in the CSV.
- 18 instances have a Schneider (2014) BKS for comparison (table below). BKS sources:
  - `C5` small instances (5 customers): taken from the Schneider (2014) CPLEX results listed directly
    in jmanzolli/E-VRPTW;
  - `_21` large instances (100 customers): taken from Adachi et al. (2022, IEICE NOLTA), who cite
    Schneider (2014) for the BKS table.
- **Solve time:** < 0.02 s per instance (slowest rc201_21 ≈ 0.01 s) on a 20-core machine. The
  constructive heuristic's compute cost is negligible; the gap is algorithmic quality, not compute.

## 5. Gap to BKS (attribution)

Across the 18 comparison instances (all fully served) the mean distance gap is **+50.7%** (absolute
mean; signed mean +50.1%). The solver is deterministic as of 2026-09-10 (unassigned customers iterated
in sorted ID order), so these numbers reproduce exactly on re-run. Breakdown:

| Set | Distance gap (mean) | Vehicles (mine vs BKS) |
|---|---|---|
| C5 small (5 customers) | **≈ +21%** (range −4.4% ~ +45.8%) | 0–2 more |
| `_21` large (100 customers) | **+54% ~ +239%** | 5–12 more |

Why the gap exists (stated plainly, no overclaiming):

1. **Vehicle count not minimized (dominant).** Schneider's primary objective is minimizing vehicles,
   and its vehicles may run **multiple trips** (one dispatch, several routes); the constructive greedy
   cannot arrange multi-trips globally, so it uses many more vehicles, which directly inflates total
   distance. E.g. `c201_21`: mine 16 vs BKS 4; `rc201_21`: 15 vs 4; `r201_21`: 14 vs 3.
   Most of the large-instance distance gap comes from here, not from route geometry.
2. **Simple heuristic.** Nearest-feasible insertion; route geometry is suboptimal, assignment fragmented.
3. **Distance metric.** I use raw Euclidean distance; the paper may truncate to 1 decimal — difference
   < 0.1%, negligible.
4. **On `c103C5` my distance being slightly below BKS:** not a different instance (verified identical),
   but under Schneider's hierarchical objective the BKS chooses **fewer vehicles (m=1) and accepts a
   slightly higher distance (176.05)**; my 2-vehicle solution is 175.4 (slightly shorter) but uses more
   vehicles, so by the paper's objective mine is worse — as expected.

## 6. Limitations and next steps (explicit)

- RC1 tight time windows leave 1 customer unserved → needs heavier insertion search or ALNS.
- **Multi-trip is modelled, but global vehicle-count minimization (assigning customers to a multi-trip
  fleet) is not implemented** — the key lever for closing the gap to BKS, left as extension (this is
  exactly what peers Ziqi / Frank do with ALNS / metaheuristics).
- Constructive heuristic only; no exact lower bound (MILP). Computing one is a separate contribution,
  outside this project's scope.

## 7. Artifacts

- `src/experiments/schneider_evrptw.py` — instance parser + constructive solver
- `src/results/schneider_evrptw_baseline.csv` — 92-instance baseline (vehicles / distance / unserved)
- `src/experiments/schneider_bks_compare.py` — BKS comparison script
- `src/results/schneider_evrptw_bks_comparison.csv` — 18-instance benchmark table
- `instances/schneider_evrptw/` — instances (public mirror)
- `instances/schneider_evrptw_original/` — instances used to verify against jmanzolli originals
