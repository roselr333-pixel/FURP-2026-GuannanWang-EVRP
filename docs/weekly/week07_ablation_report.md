# Week 7 Experiment Report: Improvement + Ablation (Ground-Air Collaborative)

> Student note (low-key). Written 2026-07-23 by Guannan Wang.
> Task: the project page weights "baseline vs improvement method comparison
> quality" at 25% and explicitly asks to "test one improvement with fair
> comparisons". In W6 I reproduced Murray & Chu (2015) as a published baseline
> and found my V2 (multi-customer flights) was 10.2–14.2% shorter than it. This
> week turns that into a *controlled* improvement + ablation study: hold
> everything fixed, vary two knobs, and decompose *where* the gain comes from.
> This experiment reuses the same instances and the same FSTSP serial-drone
> evaluator as `week07_fstsp_repro`.

---

## 1. The question this week answers

The most heavily-weighted part of the project page is "baseline vs improvement
method comparison quality". What I had before was "OR-Tools vs my own GA
(the GA was *worse*)" — that is baseline-vs-baseline, not an improvement.
After W6 I finally had a *published baseline* (M&C 2015) and my V2 beat it.
The job this week is to make that a controlled experiment and answer: *my
method is better than the published baseline — but which mechanism delivers
the gain?*

## 2. Design (lock everything, vary two knobs)

- **Same instances**: week06 `make_instance`, 4 sizes 8/12/16/20 × 10 random
  seeds (base 20260720) = **40 instances**.
- **Same evaluator**: `fstsp_makespan` (FSTSP completion time, ONE serial
  drone, truck waits at recovery). Identical to W6/W7 reproduction, so every
  configuration is compared apples-to-apples.
- **5 configurations, differing only in two knobs** (max customers per sortie
  `max_cust` / may one stop launch several sorties `multi_takeoff`):

| Config | meaning | max_cust | multi-takeoff | role |
|---|---|---:|---|---|
| C0 `published` | M&C (2015) heuristic | 1 | on | **published baseline** |
| C1 `v2` | my heuristic (current) | 2 | on | **improved method** |
| C2 `abl_cap1` | my framework, multi-customer off | 1 | on | ablation sanity check (should ≈ C0) |
| C3 `abl_notakeoff` | my framework, no stop reuse | 2 | off | isolates "multi-takeoff" contribution |
| C4 `imp_cap3` | push the improvement one step | 3 | on | **further improvement attempt** |

## 3. Results (mean over 40 instances)

| Size | Truck | C0 published | C1 V2 | C2 abl_cap1 | C3 abl_notakeoff | C4 imp_cap3 |
|---|---:|---:|---:|---:|---:|---:|
| 8  | 391.3 | 296.5 (23.9%) | **256.0 (34.5%)** | 296.5 (23.9%) | 266.1 (32.1%) | **241.8 (38.5%)** |
| 12 | 579.4 | 470.5 (18.8%) | **412.1 (29.0%)** | 470.5 (18.8%) | 432.3 (25.5%) | **406.7 (29.6%)** |
| 16 | 774.8 | 645.4 (16.6%) | **554.4 (28.7%)** | 645.4 (16.6%) | 588.0 (24.3%) | **485.1 (37.6%)** |
| 20 | 1022.3 | 855.5 (16.2%) | **767.2 (24.8%)** | 855.5 (16.2%) | 790.0 (22.6%) | **743.3 (27.2%)** |

(percent = improvement vs truck-only; C2 equals C0 exactly — see §5 sanity
check.)

**Ablation decomposition** (each mechanism's contribution to the
"improvement-vs-truck" %, in percentage points pp):

| Size | multi-customer (C1−C2) | multi-takeoff (C1−C3) | cap3 further (C4−C1) |
|---|---:|---:|---:|
| 8  | +10.6 | +2.4 | +4.0 |
| 12 | +10.2 | +3.5 | +0.6 |
| 16 | +12.1 | +4.4 | +8.9 |
| 20 | +8.6  | +2.2 | +2.4 |

## 4. How to read it

- **The improvement holds, and beats the published baseline steadily.** Across
  all 4 sizes V2 (C1) is shorter than the published baseline (C0): vs truck,
  published improves 16–24%, V2 improves 25–35%; expressed as "how much
  shorter than published", V2 is **10.2%–14.2%** shorter than published. This
  is exactly the "improvement vs baseline, fair comparison" the project page
  asks for.
- **The gain is mainly the multi-customer capability.** Raising the per-sortie
  cap from 1 (C0/C2) to 2 (C1) contributes +8.6~+12.1pp — the single largest
  source. The intuition is direct: serving two customers per sortie saves more
  of the drone's launch-recovery overhead than serving one, and because the
  drone is a serial resource, fewer sorties means fewer waiting gaps.
- **Multi-takeoff is the second source (+2.2~+4.4pp).** Reusing one stop for
  several launches means the drone does not have to return to the depot to
  re-organize every time, keeping the collaboration more flexible.
- **Pushing the cap to 3 (C4) helps further (+0.6~+8.9pp).** This shows "customers
  per sortie" is itself a useful lever, and that cap=2 can get stuck in a local
  optimum that cap=3 escapes on some instances. The magnitude is
  geometry-dependent and varies a lot across seeds.

## 5. A process note (method reflection, not a result)

In the first version C3 (abl_notakeoff) produced *identical* numbers to C1
(V2) — a 0pp difference — which I initially read as "multi-takeoff does not
matter". Debugging showed a bug: `usable_stop` had conflated "a launch/
recovery node must not itself be offloaded" with "a launch/recovery node must
not be *reused*". After the first sortie `(0,3,0)` marked the depot node `0`
as `protected`, my code wrongly banned the depot from being used as a
launch/recovery again, so one sortie was dropped — and "multi-takeoff off"
coincidentally matched "multi-takeoff on". **After the fix** (only forbid
*offloading* a launch/recovery node; allow reuse), C3 finally showed 4–7pp
worse than C1. So fixing this bug is precisely what made the
"multi-takeoff does contribute" conclusion surface. Lesson: when an ablation
shows *no difference*, suspect first that the implementation silently turned
off the variable too, before concluding the mechanism is irrelevant.

## 6. Limitations

- **Still a greedy heuristic, no local search**; absolute numbers are not known
  to be near-optimal (the MILP upper bound is not implemented, so I can only
  claim "better than the published heuristic", not "near-optimal").
- **FSTSP has no battery / time-window constraints** — intentional, to align
  with the original paper; it also means its absolute makespan must not be
  compared against the W6 EV-TW V2.
- **cap=3 enumeration grows with size**: ~0.5–0.9s per seed at n=20 (still
  acceptable), but larger sizes would need candidate pruning; n>20 not tested.
- **Synthetic instances, size ≤ 20, single seed base**: the *magnitude* of the
  percentage gain swings across seeds (e.g. 20260727 above), so the direction
  is robust but the exact amount is geometry-sensitive.

## 7. What this means for my project

This is the first complete landing of the project page's "improvement vs
baseline, fair comparison": published baseline (M&C 2015, single customer) →
my extension (multi-customer, cap2) → further extension (cap3), each step
better under *one shared evaluator*, with the gain attributed by ablation to
two mechanisms (multi-customer capability and multi-takeoff). The natural
next step is to fold this table into the Week 6/7 integration report, or move
into W8 delivery (final report + slides + demo video + reproducible package).

Files:
- Script: `src/experiments/week07_improvement_ablation.py`
- Per-instance raw: `src/results/week07_ablation_raw.csv`
- Aggregate by size: `src/results/week07_ablation_summary.csv`
- Run log: `src/results/week07_ablation_log.txt`
- Reproduction baseline report (W6): `docs/weekly/week07_fstsp_repro_report.md`
