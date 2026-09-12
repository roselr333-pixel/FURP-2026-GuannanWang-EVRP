# Week 7 Report — Reproducing Murray & Chu (2015) FSTSP and Benchmarking Against My Heuristic

> Student note (low-key). Written 2026-07-23 by Guannan Wang.
> Task: reproduce one published method (Schneider 2014 or Murray & Chu 2015) and put it in the same table as "my heuristic".
> I chose **Murray & Chu (2015) — the Flying Sidekick TSP (FSTSP)** because it is the founding paper of truck-drone collaboration and matches my project's Ground-air theme. PDF: `learning_guide/papers/The_Flying_Sidekick_TSP.pdf`.

---

## 1. What I reproduced

The FSTSP: one truck + **one drone**, the drone is carried by the truck, launched from a truck stop, serves a customer, and is recovered at a later truck stop (the rendezvous/synchronization constraint). Objective: minimize completion time (makespan = the time the truck returns to the depot carrying the drone).

The paper gives both an exact MILP and a heuristic. I reproduced the **heuristic** (Section 3.3, Algorithms 1–4): the MILP alone takes hours even for 10 customers, and a heuristic is what the paper recommends for practical sizes — also the right comparison type for my own heuristic work.

Heuristic logic (Algorithms 1–4):
1. Solve a TSP so the truck visits every customer (I use nearest-neighbor, consistent with the paper's "presume solveTSP returns a route").
2. Greedily re-assign customers from truck to drone: for each truck customer j, try every launch node i and recovery node k (i before k on the route); accept the move with the best positive **net saving = truck time saved − drone-induced delay**; repeat until no positive move remains.
3. Feasibility: a drone sortie's length must not exceed endurance. I map this to "flight distance ≤ drone range R_D".

## 2. Keeping the comparison fair ("same stage")

- **Identical instances**: I reuse week06's `make_instance`, i.e. the same customer coordinates as the V0/V1/V2 experiments (4 sizes 8/12/16/20 × 10 seeds = 40 instances).
- **One shared evaluator** `fstsp_makespan`: FSTSP completion time — the truck drives its route and waits at a recovery node if the drone has not landed; the drone is a **single serial resource** (a new sortie may only launch after the previous one is recovered). I had to fix an early bug here: I initially let one drone behave like many in parallel, which produced absurdly low makespans (e.g. 70 for N=8); after enforcing serial sequencing the numbers became sensible.
- **Only difference between the two methods**: how many customers one sortie may serve.
  - Published method (faithful): one customer per sortie (paper's Algorithm 4 candidate is launch→j→recover).
  - My V2 (FSTSP mode): up to two customers per sortie and one stop may launch several sorties — my extension beyond the original. Battery and time windows are switched off here because FSTSP does not include them.

## 3. Results (40 instances, 10 seeds/size, means)

| Size | Truck-only | Published M&C2015 | My V2 (FSTSP) | Pub vs truck | My vs truck | My vs Pub | Offload (Pub / My) |
|---|---:|---:|---:|---:|---:|---:|---:|
| 8 | 391.3 | 296.5 | **256.0** | 23.9% | 34.5% | **+13.1%** | 1.5/8 · 2.5/8 |
| 12 | 579.4 | 470.5 | **412.1** | 18.8% | 29.0% | **+12.5%** | 1.5/12 · 3.1/12 |
| 16 | 774.8 | 645.4 | **554.4** | 16.6% | 28.7% | **+14.2%** | 2.4/16 · 5.5/16 |
| 20 | 1022.3 | 855.5 | **767.2** | 16.2% | 24.8% | **+10.2%** | 2.8/20 · 5.6/20 |

(makespan units; "+" means my method is shorter. Offload rate ≈ Pub 19–30% / My 44–51%.)

**Reading the table**:
- The published method itself helps: handing 2–5 customers to the drone shortens completion time by ~20–27% vs truck-only, consistent with what I expected when tracing the algorithm by hand.
- My V2, under the same FSTSP setting, is on average 8–22% shorter than the published method and offloads roughly twice as many customers. The reason is straightforward: serving two customers per flight is more efficient than one per flight given the drone is a serial resource — fewer sorties means less waiting.
- Both are far from the absolute numbers of my week06 EV-TW V2 (a different problem with battery/time windows and a faster drone); that comparison is not valid here. This table only addresses the FSTSP setting.

## 4. Limitations

- **Heuristic only, no MILP.** The paper's MILP provides optimal bounds for small instances and validates heuristic quality; I have not implemented it, so I cannot yet say how far my heuristic is from optimum — only that it beats the published heuristic.
- **Synthetic, small instances.** Customers are placed on a ring (week06 generator), not the paper's real/standard instances; sizes stop at 20. Robustness needs larger, more realistic instances.
- **Single seed group.** 10 seeds from one base; a different initialization could shift results slightly.
- **No battery / time windows.** Deliberate (to align with the paper); this is exactly the part my week06 EV-TW V2 adds back, so do not compare against week06's absolute makespan.

## 5. Why this matters for my project

Putting Murray & Chu 2015 in the same table gives my "improvement story" a **published baseline** for the first time, instead of only comparing within my own V0/V1/V2. The natural next step for the Week 6/7 integration note is to use this table as "published baseline vs my extension": the original paper does single-customer sorties, and my extension (multi-customer flights) further shortens completion time under the same setting.

Files:
- Script: `src/experiments/week07_fstsp_repro.py`
- Per-instance raw: `src/results/week07_fstsp_raw.csv`
- Aggregated by size: `src/results/week07_fstsp_summary.csv`
- Run log: `src/results/week07_fstsp_log.txt`
- Paper PDF: `learning_guide/papers/The_Flying_Sidekick_TSP.pdf`
- Reading note: `learning_guide/papers/03_murray_chu2015_fstsp.md`
