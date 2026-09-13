# Drone energy and payload model (extension)

> Written 2026-09-13. On the main line the drone's only limit is, by default, the range constant
> `R_D` (a sortie's flight distance must not exceed 160), which means the drone is
> not electric while the project is about electric routing. This note adds the two
> limits a real multi-rotor drone has -- a payload capacity and an energy budget
> that grows with the load on board -- and re-runs the core ablation to see what
> changes.

## 1. The model

- **Payload capacity `P_MAX`**: the total demand carried in one sortie.
- **Energy budget `E_D`**: a sortie's energy is

  $$E = \sum_{\text{legs}} (\alpha + \beta \cdot \text{payload still on board on that leg}) \times \text{leg distance}$$

  i.e. flying is more expensive while the goods are still on board.
- Parameters: `ALPHA = 1.0`, `BETA` default `0.02`, `E_D = 160`, `P_MAX = 30`.
- **With `BETA = 0` and `E_D = R_D` the energy budget is exactly the old range
  limit**: the self-test compares 300 random plans against
  `cpsat_fstsp.fstsp_makespan_clean` with zero mismatches, and the greedy
  reproduces `clean_greedy`'s solution at n=8/12 (identical offloaded customer sets).
- The rest of the physical model is unchanged: a launch precedes its recovery, one
  serial drone (a sortie starts only after the previous one is recovered), the
  truck waits at the recovery node, infeasible plans return `inf`. Code:
  `src/experiments/drone_energy.py`.
- **The same two gates sit on both main-line evaluators**: `v3_ev_collab.ev_collab_k`
  (V3: battery, charging, time windows, K drones) and
  `week07_fstsp_repro.fstsp_simulate[_multi]` (W7/W8) take the four parameters
  `alpha`/`beta`/`ed`/`p_max`, defaulting to `beta = 0`, `ed = R_D` and no
  payload cap — i.e. exactly the range model, so the committed numbers stand.
  Section 4b reports what switching them on does there.

## 2. How

- Four configurations (cap1 / v2 / notakeoff / cap3) plus the published Murray &
  Chu (2015) insertion heuristic, on the same two instance sets as the earlier
  ablations: 40 synthetic (10 seeds x N=8/12/16/20) and 48 standard Solomon
  (4 families x 3 customer windows x 4 sizes).
- Three settings of the payload coefficient: `BETA` = 0.00 / 0.02 / 0.04.
  **The `BETA = 0` row doubles as the control against the committed ablation.**
- The published heuristic is not energy-aware, so its plans are simply
  re-evaluated; its feasibility rate under the model is reported separately.

## 3. Results

Means over sizes (the full per-size table is in
`src/results/drone_energy_summary.csv`):

| Metric | BETA=0.00 | BETA=0.02 | BETA=0.04 |
|---|---:|---:|---:|
| Multi-customer gain (synthetic, pp) | +10.4 | +8.6 | +6.1 |
| Multi-customer gain (standard, pp) | +6.6 | +6.1 | +5.4 |
| Published heuristic feasible (synthetic) | 1.00 | 0.62 | 0.42 |
| Published heuristic feasible (standard) | 0.92 | 0.62 | 0.48 |
| My greedy feasible (all configs, both sets) | 1.00 | 1.00 | 1.00 |
| v2 customers offloaded (synthetic / standard) | 4.2 / 3.1 | 4.3 / 3.2 | 4.0 / 3.5 |

The `BETA = 0` row matches the committed ablation item by item: v2 against
truck-only is 34.5 / 29.0 / 28.7 / 24.8% at N=8/12/16/20 and the multi-customer
gain is 10.6 / 10.2 / 12.1 / 8.6pp, identical to
`week07_ablation_summary.csv`. cap3 differs slightly because this greedy does not
carry the early pruning that `week07_improvement_ablation` uses.

Figure: `figures/drone_energy.png`.

## 4. What it says

1. **The payload/energy model erodes the multi-customer advantage without removing
   it**: on the synthetic set the gain falls from +10.4pp to +6.1pp (about 41%
   lower) and on the standard set from +6.6pp to +5.4pp (about 18% lower). The
   direction is unchanged.
2. **cap3 stops paying under the energy model**: on the synthetic set its
   decomposition is −0.5 to +0.4pp at every BETA. A three-customer sortie pushes
   the load into the range where the energy penalty starts to bite, and the payload
   capacity binds more often.
3. **Whether energy is in the model decides whether a plan is feasible at all**:
   the published heuristic, which has no energy awareness, produces plans that are
   only 42% (synthetic) and 48% (standard) energy-feasible at BETA = 0.04, while my
   greedy is 100% feasible at every BETA and every size because it checks energy
   and payload while it builds a candidate.
4. The number of offloaded customers barely moves with BETA (4.2 to 4.0 on the
   synthetic set) while the advantage clearly drops: the payload penalty changes
   what a multi-customer sortie is *worth*, not how many customers the drone can
   still take.

## 4b. The same gates on the two main-line settings

The gates are not special to the ablation runner above: `v3_ev_collab.ev_collab_k`
(V3: electric truck, charging stations, time windows, K drones) and
`week07_fstsp_repro.fstsp_simulate[_multi]` (the W7/W8 FSTSP evaluator) accept the
same four parameters, so `src/experiments/drone_energy_mainline.py` switches them
on in both. 4 sizes x 10 seeds x K = 1/2/3, `beta` = 0.00 (control) and 0.02, with
`E_D = 160` and `P_MAX = 30`.

| Model | Config | BETA = 0.00 | BETA = 0.02 | Change | Feasible at 0.02 |
|---|---|---:|---:|---:|---:|
| V3 (EV + TW) | greedy | 643 | 664 | +3.2% | 100% |
| V3 | LNS K = 1 | 513 | 521 | +1.5% | 100% |
| V3 | LNS K = 2 | 413 | 444 | +7.5% | 100% |
| V3 | LNS K = 3 | 361 | 390 | +8.1% | 100% |
| W8 (FSTSP) | greedy | 497 | 508 | +2.2% | 100% |
| W8 | LNS K = 1 | 407 | 407 | +0.1% | 100% |
| W8 | LNS K = 2 | 318 | 334 | +4.8% | 100% |
| W8 | LNS K = 3 | 276 | 295 | +7.0% | 100% |

Mean makespan over the four sizes (per-size values, the truck-only levels and the
per-instance rows are in `src/results/drone_energy_mainline_{raw,summary}.csv`;
figure `figures/drone_energy_mainline.png`). The `BETA = 0` column reproduces
`v3_ev_collab_summary.csv` and `week08_multidrone_summary.csv` value for value, so
it doubles as the control for the refactor that added the parameters.

1. **The gates cost a few percent, not the result.** The gains over truck-only
   barely move: V3 K = 1 goes 52.4% -> 53.0% at N=8 and 33.5% -> 34.5% at N=20,
   V3 K = 3 goes 72.5% -> 72.4% and 48.3% -> 46.0%; on W8 K = 3 goes 69.6% ->
   70.6% at N=8 and 54.0% -> 51.2% at N=20. The one clear loser is the single-drone
   greedy on V3, 29.0% -> 21.6% at N=16: with no improvement phase it keeps
   payload-heavy sorties whose energy it then has to pay for.
2. **Extra drones lose part of their edge.** K = 1 -> K = 3 shortens the makespan by
   42.1 / 42.2 / 27.2 / 22.3% at N = 8/12/16/20 under the range-only model, and by
   41.3 / 42.4 / 18.6 / 17.1% once the gates are on (W8: 46.6 / 40.8 / 32.6 / 21.2%
   -> 49.4 / 39.1 / 23.0 / 15.9%). The third drone is worth 5-10 pp less at
   N >= 16, where the payload cap and the energy budget start to bind together.
3. **Everything my solvers return stays feasible** (100% in all 16 size x config
   cells, and zero payload or energy violations among the K = 1 plans), because the
   gates are checked while candidates are built. That is the same awareness the
   published heuristic lacks in section 3, where only 42-48% of its plans are
   energy-feasible: being energy-aware is cheap, ignoring the battery is not.
4. **The offloaded volume is unchanged** (V3: 5.8 customers per instance at K = 1
   either way, 9.5 -> 9.4 at K = 3; W8: 8.5 -> 9.2 at K = 3). As in section 4, the
   gates change what a sortie is worth, not how many customers the drone takes.

## 5. Limitations

- The energy model is a linear surrogate (`alpha + beta x payload`): no aerodynamic
  terms and no hover or take-off/landing energy.
- The parameters (`ALPHA`, `BETA`, `E_D`, `P_MAX`) are assumed rather than
  calibrated to a specific airframe, which is why BETA is swept.
- The published heuristic's improvement at BETA > 0 is averaged only over the
  instances where it is feasible, so the two sets of percentages are not directly
  comparable; it is evidence about model awareness, not a performance comparison.
- The drone's charge is reset on recovery (battery-swap assumption), as on the main
  line; the main-line run below covers K = 1/2/3 drones, but the model is not
  fitted to a specific airframe or battery.

---

*Data provenance:*
- `src/results/drone_energy_raw.csv` / `_summary.csv` (88 instances x 3 BETA settings x 5 configs)
- `src/experiments/drone_energy.py` (evaluator and greedy), `src/experiments/drone_energy_ablation.py` (runner)
- §4b: `src/experiments/drone_energy_mainline.py` (V3 and W8), `src/results/drone_energy_mainline_raw.csv` / `_summary.csv`, `src/tools/gen_drone_energy_mainline_figure.py` -> `figures/drone_energy_mainline.png`
- `src/tools/gen_drone_energy_figure.py` -> `figures/drone_energy.png`
- control: `src/results/week07_ablation_summary.csv`, `week07_ablation_std_summary.csv`
