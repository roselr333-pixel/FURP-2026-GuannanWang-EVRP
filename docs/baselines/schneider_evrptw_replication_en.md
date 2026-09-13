# Schneider (2014) E-VRPTW Replication Notes (supplementary experiment)

> These notes document my own constructive replication of Schneider, Stenger & Goeke (2014),
> *The Electric Vehicle-Routing Problem with Time Windows and Recharging Stations*,
> Transportation Science 48(4). It sits beside my truck–drone EVRP project and shows that I
> also implemented the standard electric VRPTW with recharging stations from scratch and can
> benchmark it against the literature BKS. All numbers come from
> `src/experiments/schneider_evrptw.py` and `schneider_bks_compare.py` and are reproducible.
>
> The **same original instance files** also feed the truck–drone model: `std_evrp_instances.make_evrp`
> converts them into the week-6 EVRP-TW format, and `week06_standard_instances.py` re-runs the
> V0/V1/V2 line on real coordinates, time windows, stations and battery (evidence index §5c).

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

## 3. Method (constructive greedy + local search)

`src/experiments/schneider_evrptw.py`: a homogeneous fleet is modelled with **multi-trip** — one truck
may serve several routes, returning to the depot to reload and (if needed) fully recharge between trips,
matching Schneider (2014)'s fleet setting. Each trip greedily inserts the **nearest feasible customer**
in earliest-deadline order (capacity / time-window / battery all feasible; if the battery is low it
detours via the nearest station for a full recharge). Objective follows Schneider's hierarchy: minimise
vehicles first, then total distance. When `improve=True` (the default) the construction is then refined by `schneider_improve.py`: every trip is re-checked and repaired with the cheapest feasible station, whole trips may move between vehicles or merge, and customers may be relocated or swapped — a move is accepted only when the hierarchical objective improves.

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
- **Solve time:** the construction is < 0.02 s per instance; the added local search costs ~7-16 s
  on the 100-customer instances (it converges; a per-instance budget caps it), so a full 92-instance
  run takes ~14 min. The gap is algorithmic quality, not compute.

## 5. Gap to BKS (attribution)

**Headline: mean distance gap +21.3%** across the 18 comparison instances (all fully served;
vehicles 3.28 vs 2.06 BKS), down from **+52.7%** for the construction alone. Three instances
(`c208C5`, `r105C5`, `rc208C5`) now match the BKS exactly.

| stage | mean abs distance gap | mean vehicles (BKS 2.06) |
|---|---:|---:|
| constructive greedy (depot horizon enforced) | +52.7% | 5.44 |
| + local search (trip move/merge, relocate/swap, 2-opt) | **+21.3%** | **3.28** |

The solver is deterministic (the unassigned-customer set is iterated in sorted ID order), so every
number here reproduces exactly on re-run. Remaining breakdown:

| Set | Distance gap (mean) | Vehicles (mine vs BKS) |
|---|---|---|
| C5 small (5 customers) | **+10.1%** (range 0.0% to +27.1%) | 0-1 more |
| `_21` large (100 customers) | **+43.6%** (range +15.5% to +97.2%) | 2-4 more |

Why the remaining gap exists (stated plainly, no overclaiming):

1. **Fleet packing is still the dominant residual.** Schneider minimises vehicles first and its
   vehicles run several trips. My construction opens one vehicle per trip; the local search takes the
   large instances from 14-16 vehicles down to 5-9, but the BKS uses 3-4, and every extra vehicle adds
   a depot round-trip (`c201_21`: 6 vs 4; `c206_21`: 8 vs 4; `r201_21`: 9 vs 3).
2. **The local search is a hill climber.** Trip move/merge plus customer relocate/swap plus 2-opt with
   a strict acceptance rule; a ruin-and-recreate (ALNS) layer is the natural next step.
3. **The charging policy is still "nearest station, full charge".** Partial recharging buys *time*,
   which is what limits how many trips a vehicle can chain; it is the natural next lever for the
   residual vehicle gap (it does not change distance directly).

**A modelling bug found on the way.** The depot's own closing time was checked only when a trip was
appended to an existing vehicle, never for the first trip of a new vehicle, so 3 of the 18 instances
(`c103C5`, `r201_21`, `rc201_21`) returned to the depot after it had closed. The horizon is now
enforced for every trip: `build_trip` rejects any customer whose return would break it. That made the
constructive baseline slightly worse (+50.7% to +52.7%) but physically valid; the local search then
recovers far more than it lost.

## 6. Limitations and planned tasks

- **All comparison instances are fully served** (18/18 here, and no unserved customers in the
  92-instance baseline run) after the horizon fix.
- **Global fleet packing is still not solved**: the local search merges and moves trips, but the
  construction decides the initial fleet, so the 100-customer instances keep 2-4 vehicles more than
  the BKS. The next levers are (i) partial recharging (it buys time, not distance) and (ii) an ALNS /
  ruin-and-recreate layer over a trip pool.
- No exact lower bound (MILP); computing one is a separate contribution, outside this project's scope.

## 7. Artifacts

- `src/experiments/schneider_evrptw.py` — instance parser + constructive solver + the call into the local search
- `src/experiments/schneider_improve.py` — local search: station repair, trip move/merge, customer relocate/swap, 2-opt
- `src/results/schneider_evrptw_baseline.csv` — 92-instance baseline (vehicles / distance / unserved, plus the constructive stage for the before/after)
- `src/experiments/schneider_bks_compare.py` — BKS comparison script (reports both stages)
- `src/results/schneider_evrptw_bks_comparison.csv` — 18-instance benchmark table
- `instances/schneider_evrptw/` — instances (public mirror)
- `instances/schneider_evrptw_original/` — instances used to verify against jmanzolli originals
