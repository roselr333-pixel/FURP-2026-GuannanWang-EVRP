# Formal model: ground-air collaborative EVRP-TW

> This document states the truck-drone model I implemented in standard notation, as
> the modelling section of the report. It follows the code: constraints the
> evaluator actually enforces are listed as hard, constraints the search treats as
> penalties are marked separately, and things that are not implemented (capacity,
> for example) are named as such.

---

## 1. Model layers

The project is not one model but a family of variants over a shared constructive
greedy core:

| Variant | Truck | Drone | Time windows | Charging | Entry point |
|---|---|---|---|---|---|
| V0 | unlimited range (reference) | none | penalised | no | `week06_ground_air_evrp_tw.run_variant("V0")` |
| V1 | battery + charging | none | penalised | yes | `run_variant("V1")` |
| V2 | battery + charging | 1 drone, 1-2 customers per sortie | penalised | yes | `run_variant("V2")` |
| FSTSP mode | unlimited range | 1 or K drones, 1-3 customers per sortie | ignored | no | `week07_fstsp_repro.fstsp_simulate` |
| V3 | battery + charging | K drones, 1-2 customers per sortie | penalised | yes | `v3_ev_collab.ev_collab_k` |

V2 and the FSTSP mode share one completion-time evaluator (V2 adds the battery and
time-window layer); V3 puts that layer back on top of the collaborative model.
Sections 2-5 describe the core model, section 6 the variant differences.

---

## 2. Sets and indices

| Symbol | Meaning |
|---|---|
| $0$ | depot, start and end of the truck route |
| $C = \{1,\dots,n\}$ | customers |
| $S$ | charging stations (four in the synthetic instances; empty in FSTSP-mode instances) |
| $V = \{0\} \cup C \cup S$ | nodes |
| $A = \{(a,b) : a,b \in V,\ a \neq b\}$ | arcs |
| $C_{\text{truck}}$ | customers served by the truck |
| $T = \{(i_k, C_k, j_k)\}_{k}$ | sorties: launch node $i_k$, ordered customer sequence $C_k$, recovery node $j_k$ |

$d_{ab}$ is the Euclidean distance between nodes $a$ and $b$. Geometry comes from
either the random circular generator (weeks 6-7) or the official Solomon topologies
(week 8, translated so the depot is at the origin and rescaled to the same RMS
customer radius).

---

## 3. Parameters

| Symbol | Meaning | Value |
|---|---|---|
| $v_T$ | truck speed | 1.0 |
| $v_D$ | drone speed | 2.0 |
| $s$ | customer service time | 10 |
| $\chi$ | full recharge time at a station | 40 |
| $\rho$ | truck energy per distance unit | 1.0 |
| $Q$ | truck battery capacity | 250 |
| $R$ | drone range per sortie | 160 |
| $m$ | maximum customers per sortie | 1-3 (1-2 on the main line) |
| $K$ | number of drones | 1 (main line); 1-5 (week-8 extension) |
| $[e_i, l_i]$ | customer time window | width 220 synthetic, 35 for the tight-window cases |
| $q_i$ | customer demand | 5-15 |
| $\mathrm{CAP}$ | truck capacity per route | 1000 (enforced: the demand carried on the truck route) |
| $w$ | multi-objective weight | 0, 0.25, 0.5, 0.75, 1.0 |

---

## 4. Decision variables

- the truck route, equivalently arc variables $x_{ab} \in \{0,1\}$;
- for every customer, whether the truck or a sortie serves it;
- the sortie set $T$: launch node, ordered customer sequence and recovery node of each sortie;
- the drone assignment $\sigma: T \to \{1,\dots,K\}$ (only when $K > 1$).

---

## 5. Objective and the completion-time recurrence

The objective is the completion time (makespan): the moment the truck is back at the
depot with its drone.

$$\min\ T_{\text{end}} = a_{|\text{route}|}$$

Write the truck route as $(v_0 = 0, v_1, \dots, v_L = 0)$. Arrival times follow
($\tau$ is the node's extra time: $s$ at a customer, $\chi$ at a station, 0 at the depot):

$$a_0 = 0, \qquad a_p = a_{p-1} + \frac{d_{v_{p-1}, v_p}}{v_T} + \tau(v_p)$$

For each sortie $k$, in order of its launch position:

$$\lambda_k = a_{\text{pos}(i_k)} \quad\text{(launch)}$$

$$\phi_k = \frac{1}{v_D}\sum_{\ell} d_{\text{leg}_\ell} + s \cdot |C_k| \quad\text{(flight, including per-customer service)}$$

$$r_k = \max\bigl(a_{\text{pos}(j_k)},\ \lambda_k + \phi_k\bigr) \quad\text{(recovery)}$$

$$w_k = r_k - a_{\text{pos}(j_k)}, \qquad a_p \mathrel{+}= w_k \ \ \forall p \ge \text{pos}(j_k)$$

So **if the drone arrives late, the truck waits at the recovery node**, and the wait
shifts every later arrival. This is the standard Murray & Chu (2015) rendezvous
treatment. An earlier revision of this project took the maximum landing time over
sorties independently (which would let one drone fly two sorties at once); that is
documented and fixed in `docs/analysis/evaluator_physical_fix_note_en.md`.

---

## 6. Constraints

### 6.1 Hard constraints (a violation makes the evaluator return $+\infty$)

| ID | Constraint | Form |
|---|---|---|
| C1 | route starts and ends at the depot; each truck-served customer is visited once | $\sum_b x_{cb} = \sum_a x_{ac} = 1$ for $c \in C_{\text{truck}}$ |
| C2 | coverage: every customer is served exactly once, by the truck or by exactly one sortie | $C = C_{\text{truck}} \uplus \biguplus_k C_k$ |
| C3 | launch precedes recovery along the truck route | $\text{pos}(i_k) < \text{pos}(j_k)$ |
| C4 | sortie flight within range | $\sum_{\ell} d_{\text{leg}_\ell} \le R$ |
| C5 | customers per sortie | $1 \le |C_k| \le m$ |
| C6 | one drone is serial: a sortie launches only after the previous one has been recovered | $\lambda_k \ge r_{k-1}$; equivalently sortie intervals do not overlap |
| C7 | the drone is on the truck when the truck reaches the launch node | $r_{k-1} \le a_{\text{pos}(i_k)}$ |
| C8 | the truck waits at the recovery node | the $w_k$ shift in section 5 |
| C9 | battery (V1/V2/V3): the charge never goes negative between recharges | see 6.3 |
| C10 | $K$ drones: each sortie is assigned to one drone, each drone is serial, and at least one drone is free at launch | $\sigma(k) \in \{1..K\}$, $\lambda_k \ge \text{avail}[\sigma(k)]$ |

C6 and C7 say the same thing: **one drone flies one sortie at a time**. This is the
constraint at the centre of the FC-7-4 nested-sortie fix.

### 6.2 Soft constraints

| ID | Constraint | Treatment |
|---|---|---|
| S1 | customer time window $[e_i, l_i]$ | arriving early waits until $e_i$; arriving late increments a violation counter and does not reject the solution (`tw_viol` in V1/V2/V3) |
| S2 | time windows of drone-served customers | the heuristic filters candidate sorties with it (`_customer_list_is_feasible`); a search design choice, not a hard model constraint |

### 6.3 Battery and charging (V1 / V2 / V3)

The truck consumes $\rho \cdot d$ along its route. When the remaining charge cannot
cover the next leg, a **greedy charging policy** applies:

1. detour from the current node to the **nearest** station $s^\star$, costing $d/v_T$;
2. recharge to full there, costing $\chi$;
3. if a full battery still cannot cover the leg leaving that station, set
   $\text{energy\_inf} = \text{true}$ and treat the solution as infeasible.

This repairs feasibility; it does not optimise which station to use. On the drone
side only the per-sortie range is limited, and recovery resets it (battery-swap
assumption).

### 6.4 Multi-objective extension

`week06_multi_objective.my_v2_weighted` replaces the insertion score with a weighted
sum:

$$\text{score} = w \cdot (\text{distance saving}) + (1-w) \cdot (\text{makespan reduction})$$

$w = 0$ reproduces plain V2 and $w = 1$ optimises distance only. This is a
weighted-sum scalarisation, so the front it produces is coarse; it is not a full
Pareto solver.

---

## 7. What is and is not implemented

Implemented and reflected in the results:

- truck battery, nearest-station greedy recharging, charging detours;
- customer time windows as a penalty with a reported violation count;
- per-sortie drone range, per-customer service time, rendezvous with truck waiting;
- a single serial drone (no overlapping sorties), and explicit scheduling for $K$ drones;
- multi-customer sorties (1-3 customers) and reuse of one stop for several sorties;
- exact optima on small instances (CP-SAT, up to $n = 12$).

Not modelled, or simplified:

- **capacity is enforced on the truck, not on the drone**: the demand carried by
  the truck route may not exceed $\mathrm{CAP} = 1000$, and offloading a customer to
  the drone removes its demand from the truck. The declared value is free for
  $N \le 50$ at the generated demands and binds on part of the $N = 100$ instances;
  because one serial drone can only take ~10-20% of the demand off the truck, a
  much tighter cap stays infeasible (study: `week06_capacity_study.py`,
  `figures/capacity_binding.png`);
- **no drone energy or payload model**: only the range $R$ limits a flight;
- **recharging is not optimised**: the policy is fixed at "nearest station, full charge";
- **time windows are not hard**: both the main line and V3 count violations;
- **stations appear only in the week-6 and V3 instances**: FSTSP-mode instances have
  none and treat the truck as unlimited-range;
- **the model is static and deterministic**: no random travel or service times;
- **the per-sortie customer cap** $m \le 3$ is an enumeration-cost limit, not a
  property of the problem.

---

## 8. Where each piece lives in the code

| Model part | Implementation |
|---|---|
| truck arrivals and node extra time | `week06_ground_air_evrp_tw.simulate` / `week07_fstsp_repro.fstsp_simulate` (`node_extra` / `_service`) |
| launch, flight, recovery, waiting (single drone) | `week06_ground_air_evrp_tw.simulate`; `cpsat_fstsp.fstsp_makespan_clean` is an independent implementation used as a cross-check |
| serialisation C6/C7 | `drone_free > arr[i_pos] \Rightarrow +\infty` inside `simulate` |
| $K$ drones | `week07_fstsp_repro.fstsp_simulate_multi`; `drone_scheduling.simulate` recomputes with an explicit assignment |
| truck EV route and greedy recharging | `week06_ground_air_evrp_tw.truck_ev_route` |
| V3 (station detours + time windows + K drones) | `v3_ev_collab._truck_timeline` / `ev_collab_k` |
| exact optimum on the same physical model | `cpsat_fstsp.solve_exact` |
| coverage check C2 | `tests/test_evaluators.py::test_v3_serves_every_customer` |

The FSTSP evaluator used on the main line and `cpsat_fstsp.fstsp_makespan_clean`
agree value-for-value on random plans, so heuristic solutions and exact optima are
compared on one and the same model.
