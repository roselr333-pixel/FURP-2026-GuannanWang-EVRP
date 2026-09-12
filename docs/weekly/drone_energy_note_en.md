# Drone energy and payload model (extension)

> Written 2026-09-13. On the main line the drone's only limit is the range constant
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

## 5. Limitations

- The energy model is a linear surrogate (`alpha + beta x payload`): no aerodynamic
  terms and no hover or take-off/landing energy.
- The parameters (`ALPHA`, `BETA`, `E_D`, `P_MAX`) are assumed rather than
  calibrated to a specific airframe, which is why BETA is swept.
- The published heuristic's improvement at BETA > 0 is averaged only over the
  instances where it is feasible, so the two sets of percentages are not directly
  comparable; it is evidence about model awareness, not a performance comparison.
- The drone's charge is reset on recovery (battery-swap assumption), as on the main
  line; still single-drone only.

---

*Data provenance:*
- `src/results/drone_energy_raw.csv` / `_summary.csv` (88 instances x 3 BETA settings x 5 configs)
- `src/experiments/drone_energy.py` (evaluator and greedy), `src/experiments/drone_energy_ablation.py` (runner)
- `src/tools/gen_drone_energy_figure.py` -> `figures/drone_energy.png`
- control: `src/results/week07_ablation_summary.csv`, `week07_ablation_std_summary.csv`
