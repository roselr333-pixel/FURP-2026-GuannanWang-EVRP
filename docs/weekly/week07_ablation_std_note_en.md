# Core ablation re-run on standard (Solomon) instances

> Written 2026-09-13. This note closes a limitation I had listed: the five-config
> ablation that attributes the gain had only been run on random geometry, so
> "multi-customer sorties are the main source" could have been an artifact of the
> synthetic customer cloud. Here the same experiment is run on official Solomon
> topologies with everything else held fixed.

## 1. Why

The synthetic generator scatters customers uniformly in a ring. Real instances
cluster and follow roads. An attribution experiment that only ever sees one
geometry can end up measuring that geometry. So I change the coordinate source,
leave the rest untouched, and look at the gain decomposition again.

## 2. How

- **The heuristic code is unchanged**: this reuses `week07_improvement_ablation.my_v2_param`
  and its `CONFIGS` directly, so the five configurations (published / v2 / abl_cap1 /
  abl_notakeoff / imp_cap3) and the shared evaluator are the same objects as in the
  synthetic run. Only the instance source differs.
- **Instances**: the four distinct Solomon spatial families in the repo — C101
  (clustered), C201 (clustered, wider windows), R101 (uniform), RC101 (mixed). The
  Solomon files share coordinates within a family prefix, so "the first n customers"
  yields only one point set per family. I slide the customer window instead (start at
  customer 1 / n+1 / 2n+1), giving 4 x 3 = 12 different customer sets, times four
  sizes (N = 8/12/16/20): **48 instances** in total.
- **Coordinates**: translated so the depot is at the origin and rescaled to the same
  RMS customer radius as the synthetic generator at that n
  (`fstsp_instances.make_solomon_fstsp(name, n, start)`). Truck/drone speeds, service
  time, range and every other model constant stay as they were.

## 3. Results

Main comparison (mean over the 12 instances per size; the percentage is relative to
truck-only):

| Size | truck-only | published | V2 (mine) | abl_cap1 | abl_notakeoff | imp_cap3 |
|---|---:|---:|---:|---:|---:|---:|
| N=8  | 260.2 | 214.8 (17.3%) | **192.0 (25.4%)** | 214.8 (17.3%) | 197.1 (23.4%) | 171.4 (33.1%) |
| N=12 | 402.6 | 336.3 (15.8%) | **304.8 (23.0%)** | 336.3 (15.8%) | 313.2 (21.1%) | 291.6 (26.9%) |
| N=16 | 570.3 | 485.6 (14.7%) | **426.5 (23.6%)** | 485.6 (14.7%) | 434.9 (22.3%) | 406.5 (28.3%) |
| N=20 | 713.7 | 616.5 (12.8%) | **553.7 (21.1%)** | 616.5 (12.8%) | 565.3 (19.3%) | 517.7 (26.2%) |

Gain decomposition (percentage points of the improvement over truck-only):

| Size | multi-customer | multi-takeoff | cap3 |
|---|---:|---:|---:|
| N=8  | **+8.1** | +2.0 | +7.7 |
| N=12 | **+7.2** | +1.9 | +3.9 |
| N=16 | **+8.9** | +1.3 | +4.7 |
| N=20 | **+8.3** | +1.8 | +5.1 |

Side by side with the synthetic run (same code, same evaluator):

| Size | synthetic: multi-cust / takeoff / cap3 | standard: multi-cust / takeoff / cap3 |
|---|---|---|
| N=8  | 10.6 / 2.4 / 4.0 | 8.1 / 2.0 / 7.7 |
| N=12 | 10.2 / 3.5 / 0.6 | 7.2 / 1.9 / 3.9 |
| N=16 | 12.1 / 4.4 / 8.9 | 8.9 / 1.3 / 4.7 |
| N=20 | 8.6 / 2.2 / 2.4 | 8.3 / 1.8 / 5.1 |

Multi-customer gain by spatial family (mean over sizes and windows): C101 **5.7pp**,
C201 **5.8pp**, R101 **14.1pp**, RC101 **6.9pp**.

Figure: `figures/ablation_std.png`.

## 4. What it says

1. **The main gain source is the same on both geometries.** On standard instances
   multi-customer ability contributes **+7.2 to +8.9pp** and is the largest of the
   three; on synthetic instances it is +8.6 to +12.1pp. Multi-takeoff is smaller on
   standard instances (**+1.3 to +2.0pp** versus +2.2 to +4.4pp). The attribution is
   not a property of the customer cloud I happened to generate.
2. **The sanity check survives.** `abl_cap1` (my framework with one customer per
   sortie) matches the published baseline's makespan instance by instance on all 48
   instances, so the only real difference between my method and the published one is
   still the multi-customer capability.
3. **V2 still beats the published baseline on standard topology**: relative to
   truck-only, V2 reaches 21.1-23.6% and published reaches 12.8-15.8%.
4. **How much the multi-customer ability buys depends on the spatial pattern**: 14.1pp
   on the uniform R101 topology against 5.7/5.8pp on the clustered C101/C201. In a
   clustered instance there are fewer far-away customers for a sortie to absorb, so
   there is less detour to remove.

## 5. Limitations

- This line uses the FSTSP evaluator, so it has **no time windows and no battery**.
  The equivalent decomposition under energy and time windows would belong to the V3
  line, which does not currently have a five-configuration breakdown.
- "Standard instances" means the **coordinates come from the official Solomon files**,
  but the instances are still derived (take n customers, rescale to the synthetic
  radius) rather than the official FSTSP benchmarks themselves; the paper's original
  instances are covered in `docs/weekly/week08_mc_benchmark_note_en.md`.
- Only four distinct spatial families, and the three windows within a family share one
  spatial pattern, so the instances are not fully independent.
- Only the improvement over truck-only is reported; the absolute distance to the
  optimum is covered separately in `docs/weekly/week08_exact_gap_note_en.md`.

---

*Data provenance:*
- `src/results/week07_ablation_std_raw.csv` / `_summary.csv` (48 instances x 5 configs)
- `src/experiments/week07_ablation_std.py` (runner), `src/experiments/week07_improvement_ablation.py` (reused heuristic)
- `src/experiments/fstsp_instances.py` (Solomon instance construction)
- `src/tools/gen_ablation_std_figure.py` -> `figures/ablation_std.png`
- synthetic comparison: `src/results/week07_ablation_summary.csv`
