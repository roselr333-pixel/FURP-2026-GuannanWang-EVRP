# 实验配置与参数说明（中央表）

> 写于 2026-07-24，Guannan Wang；2026-09-13 按代码逐项核对后重写。
> 用途：让评审只看这一页就能复现我的全部实验，不用翻 30 多个脚本里散落的常量。
> 这一页直接对应"可复现性"那条评分项；下面每个值都标了出处文件。

---

## 1. 共用常量

所有卡车-无人机实验的模型常量只有一份定义，在 `week06_ground_air_evrp_tw.py`；
其余脚本一律 `import week06_ground_air_evrp_tw as w6` 后取用（`week07_fstsp_repro.py`、
`week08_*.py`、`v3_ev_collab.py`、`cpsat_fstsp.py`、`drone_scheduling.py` 都是引用，没有各自重定义）。

| 常量 | 值 | 含义 | 出处 |
|---|---|---|---|
| `V_T` | 1.0 | 卡车速度 | `week06_ground_air_evrp_tw.py` |
| `V_D` | 2.0 | 无人机速度（卡车的 2 倍） | 同上 |
| `SERVICE` | 10.0 | 每个客户的服务时间 | 同上 |
| `RECHARGE` | 40.0 | 充电站满充时间 | 同上 |
| `RHO` | 1.0 | 卡车单位距离耗电 | 同上 |
| `R_D` | 160.0 | 无人机单架次航程上限（**所有脚本都是这个值**，FSTSP 模式同样取 `w6.R_D`） | 同上 |
| `ALPHA` | 1.0 | 无人机空载时的单位距离能耗 | `drone_energy.py` |
| `BETA` | 0.02 | 每（单位距离 × 机上剩余需求）的额外能耗；两个主线评估器默认取 0（= 仅航程） | 同上 |
| `E_D` | 160.0 | 无人机单架次能耗预算；默认等于 `R_D`，即退化为航程约束 | 同上 |
| `P_MAX` | 30.0 | 单架次承载需求上限；两个主线评估器默认不限 | 同上 |
| `Q_DEFAULT` | 250 | 卡车电池容量 | 同上 |
| `CAP` | 1000 | 卡车单路线载重上限（**已启用**：路线需求之和超过即判不可行；见 §5） | 同上 |

单位约定：距离 = 速度 × 时间，所以所有时间量都以距离单位表示。

**评估器口径**：单架无人机串行（一架次回收前不能起飞下一个）、卡车在回收点等待、
架次航程不超限；违反任一条返回 `inf`。这条口径在 2026-09-13 统一到
`week07_fstsp_repro.fstsp_simulate` 与 `week06_ground_air_evrp_tw.simulate` 两处，
新旧对照见 `docs/analysis/evaluator_physical_fix_note_zh.md`。

**能耗/载荷闸门**：`v3_ev_collab.ev_collab_k` 与 `week07_fstsp_repro.fstsp_simulate[_multi]`
都接受 `alpha` / `beta` / `ed` / `p_max` 四个参数；默认 `beta=0, ed=R_D, p_max=∞`
与原来的航程模型逐位一致，所以已提交的数字不受影响。打开后架次还要满足载荷上限与
能耗预算，见 §4 的能耗实验行与 §5。

## 2. 算例来源

| 数据集 | 位置 / 生成方式 | 规模 | 用在哪 |
|---|---|---|---|
| 合成环形算例 | `w6.make_instance(n, seed)` | n = 8 – 100 | week06 / 07 / 08 的主线 |
| 官方 Solomon VRPTW | `src/instances/official_solomon/*.vrp` + `.sol`（BKS） | 56 个实例 | 三基线对比 |
| 标准 Solomon 派生的 FSTSP 算例 | `fstsp_instances.make_solomon_fstsp(name, n, start)` | 4 族 × n = 10/20/30/50（W8）；4 族 × 3 顾客窗口 × n = 8/12/16/20（W7 消融） | 标准拓扑上的协同实验 |
| Murray & Chu (2015) 原始 FSTSP 算例 | `src/instances/murray_chu_2015/` | 36 个 10 顾客实例（11 个带文献 OFV） | 论文原始算例对比 |
| Schneider (2014) E-VRPTW | `src/instances/schneider_evrptw/`、`schneider_evrptw_original/` | 92 个实例（18 个有 BKS 可对照） | 侧线复现；求解器 = 构造式贪心 + 局部搜索（`schneider_improve.py`） |

合成算例的构造（`make_instance`）：仓库固定在原点 `(0,0)`；客户取极坐标，
半径 `r ~ U[15, 30+4n]`、角度 `U[0, 2π)`；4 个充电站固定在 `(±45, 0)`、`(0, ±45)`；
客户时间窗起点 `e ~ U[0, 120]`、宽度 220（`tw_tight=True` 时宽度 35）；
需求 `q ~ U{5, …, 15}`。位置、时间窗、需求全部由种子决定，因此可精确复现。

标准 Solomon 算例的构造（`fstsp_instances`）：取官方坐标，平移到仓库为原点，
再等比缩放到与该规模下合成生成器相同的顾客 RMS 半径，模型常量不变。
仓库里的 Solomon 文件在同一族前缀内共享坐标，所以另加了 `start` 参数滑动顾客窗口，
以得到同一拓扑下的多组不同顾客集。

## 3. 各实验的规模与种子

| 脚本 | 规模 | 种子 | 备注 |
|---|---|---|---|
| `week06_ground_air_evrp_tw.py` | N = 8/12/16/20 | 10 个：20260720–20260729 | V0（无电池）/ V1（纯电）/ V2（协同）同台 |
| `week06_largeN.py` | N = 30/50/100 | 5 个：20260820–20260824 | 规模衰减 |
| `week06_capacity_study.py` | N = 8/12/16/20/30/50/100 | 5 个：20260720–20260724 | 载重是否 binding；cap ∈ {1000, 600, 400} + 无限载重参照 |
| `week06_standard_instances.py` | 6 族 × N = 8/12/16/20 × 4 个子集 = 96 | 确定性（子集代替种子） | 标准算例（Schneider 2014 原始数据）复跑；实例由 `std_evrp_instances.py` 映射 |
| `week06_sensitivity.py` | N = 12 | 5 个：20260910–20260914 | 扫 `Q ∈ {120,180,250,350,500}`、`R ∈ {60,90,120,160,200}`、`K ∈ {1,2,3}`、`N ∈ {8,12,16,20,30}` |
| `week06_multi_objective.py` | N = 12 | 5 个：20260910–20260914 | 加权和 `w ∈ {0, 0.25, 0.5, 0.75, 1.0}`；目标里含无人机能耗代理项 `DRONE_RHO = 0.3` |
| `week07_fstsp_repro.py` | N = 8/12/16/20 | 10 个：20260720–20260729 | M&C (2015) 插入启发式 vs 我的 V2 |
| `week07_improvement_ablation.py` | N = 8/12/16/20 | 10 个：20260720–20260729 | 五配置消融（合成算例） |
| `week07_ablation_std.py` | 4 族 × 3 窗口 × N = 8/12/16/20 = 48 | 确定性 | 同一套启发式与评估器，换 Solomon 拓扑 |
| `week08_lns.py` | N = 8/12/16/20/30/50 | 10 个：20260720–20260729 | 迭代预算 `{8:300, 12:300, 16:300, 20:400, 30:250, 50:150}`；模拟退火初温 = 当前 makespan 的 5% |
| `week08_multidrone.py` | 同 `week08_lns` 的 6 个规模 | 10 个：同上 | K = 1/2/3 |
| `week08_multidrone_std.py` | 4 族 × N = 10/20/30/50 | 确定性（`LNS_SEED = 20260720`） | K = 1/2/3/5；精确调度只跑架次数 ≤ 14 的配置 |
| `week08_exact_gap.py` | n = 8/10/12/14/16 | 5 个：20260720–20260724 | CP-SAT 每规模时间上限 30/60/90/90/120 s；把启发式最优解同时传成目标上界与 `AddHint` 热启动 |
| `week08_mc_benchmark.py` | 36 个原始算例 | `SEED = 20260720` | K = 1/2/3，每架次顾客上限 1/2/3 |
| `v3_ev_collab.py` | N = 8/12/16/20 | 10 个：20260720–20260729 | K = 1/2/3；greedy 与 greedy + LNS |

种子约定：多种子实验一律用固定种子集，不用系统时间；确定性脚本在日志里注明。

## 4. 求解器设置

| 求解器 | 参数 | 值 | 出处 |
|---|---|---|---|
| OR-Tools | `first_solution_strategy` | `PARALLEL_CHEAPEST_INSERTION`（紧时间窗下 `PATH_CHEAPEST_ARC` 找不到可行初解） | `benchmark_official_solomon.py` |
| OR-Tools | `local_search_metaheuristic` | `GUIDED_LOCAL_SEARCH` | 同上 |
| OR-Tools | 每实例时间上限 | 10 s | 同上 |
| OR-Tools | 距离标度 | ×10 取整（Solomon 原坐标为整数） | 同上（`DIST_SCALE = 10`） |
| GA（自写） | `POP_SIZE` / `N_ELITE` / `TOURNAMENT` / `MUT_RATE` | 40 / 6 / 4 / 0.30 | `baseline_ga_vrptw.py` |
| GA | 每实例时间上限 | 8 s | 同上（`TIME_LIMIT_S = 8`） |
| GA | 车辆数偏离 BKS 的罚项 | 1000 / 车 | 同上 |
| GA | 解码与局部搜索 | Solomon I1 插入 + intra-route 2-opt + inter-route relocate | 同上 |
| GA | 种子 | 5 个：20260717 / 20260801 / 20260815 / 20260901 / 20261001，报表取均值 | 同上 |
| PyVRP | 版本 | 0.14.0（`baseline_pyvrp_vrptw.py`） | 与官方 `.sol` BKS 对照 |
| CP-SAT | 时间上限 / workers | 每规模 30–120 s / 8 | `week08_exact_gap.py`、`cpsat_fstsp.solve_exact` |
| CP-SAT | 热启动 | `upper_bound`（目标截断）+ `hint`（路线/架次/位序） | `cpsat_fstsp.solve_exact` |
| Schneider 局部搜索 | `improve` / `improve_moves` / `improve_budget` | True / 400 步 / 60 s | `schneider_evrptw.py` → `schneider_improve.improve_solution` |
| 无人机能耗（主线） | `beta` / `ed` / `p_max` | 0.00、0.02 / 160 / 30 | `drone_energy_mainline.py`（V3 与 W8，K=1/2/3） |
| 无人机能耗（消融） | `beta` | 0.00 / 0.02 / 0.04 | `drone_energy_ablation.py` |

PyVRP 固定了 seed，重复运行结果一致；OR-Tools 用 `GUIDED_LOCAL_SEARCH` + 10 s 时间预算，该版本的 routing 参数不暴露随机种子，所以同一算例的搜索结果逐次有小幅浮动——56 实例的均值 gap 我实测在 7.2%~8.1% 之间，本仓库报单次结果并给出这个区间。GA 是唯一需要多种子的基线，报 5 种子均值 ± 标准差。

## 5. 已声明但未启用的项（写报告时要如实说明）

- **`CAP = 1000`（卡车载重）已启用**：`truck_ev_route` 与 `simulate` 都检查路线上承载的需求之和，
  超过即 `cap_inf`/不可行；V2 卸载顾客时其需求也随之离开卡车，因此贪心会先"修"超载再优化。
  在生成的需求下 `CAP=1000` 对 N≤50 不 binding，N=100 有 1/5 算例 binding；单架串行无人机
  最多只能卸下约 10–20% 的需求，所以更紧的 cap 仍会不可行（研究见 `week06_capacity_study.py`、
  `figures/capacity_binding.png`）。
- **无人机的能耗/载荷闸门默认关闭**：主线评估器只限制单架次航程 `R_D`；载荷上限
  `P_MAX` 与能耗预算 `E_D`（`drone_energy.py`）是可选约束，`v3_ev_collab.ev_collab_k`
  与 `week07_fstsp_repro.fstsp_simulate[_multi]` 都接受。回收仍视为换电池、逐架次复位。
  `drone_energy_mainline.py` 在 `beta=0.02` 下把闸门打开重跑 V3 与 W8，`beta=0` 一行
  用于复现原来的数字（图 `figures/drone_energy_mainline.png`）。
- **时间窗是罚项不是硬约束**：V1/V2/V3 报 `tw_viol` 计数，但不因超窗拒绝解。
- **充电策略是贪心**：电量不足时绕到最近的充电站满充，不优化选哪个站。

## 6. 路径与文件约定

- **结果**：`src/results/*.csv`（按 `.gitignore` 不入库，靠脚本 + 种子重新生成）、
  `src/results/*.txt` / `*.log`（日志入仓；全部 UTF-8，用 PowerShell 的 `Tee-Object` 存日志时要显式指定编码）
- **实例**：`src/instances/`
- **实验脚本**：`src/experiments/`；绘图与仪表盘生成器：`src/tools/`
- **文档**：`docs/reference/`（本表、证据索引、形式化模型、失败案例）、
  `docs/analysis/`、`docs/weekly/`、`docs/baselines/`；总索引见 `docs/README.md`
- **自学笔记**：`learning_guide/`（不进提交仓库）
- **一键复现**：`run_all.py`；每个数字到脚本的对照见 `REPRODUCE.md`

---

*这一页之后任何脚本改参数，都要回来更新对应行。*
