# 实验配置与参数说明（中央表）

> 写于 2026-07-24，Guannan Wang。
> 用途：让评审或同组同学只看这一页就能复现我全部实验，不用翻 7 个脚本里散落的常量。
> 缺这一页是"可复现性 25%"那条评分项最常扣分的地方（见 `progress_report.md` §3.2-①）。

---

## 1. 全局共用的算例构造

| 项 | 值 | 出处 / 备注 |
|---|---|---|
| 客户坐标 | 合成环形布局：仓库在原点 `(0,0)`、客户在仓库周围一个环上随机散布 | `week06_ground_air_evrp_tw.py::make_instance` |
| 充电站数量 | 4 个（每个客户规模） | 同上；坐标由 `SEED` 唯一确定 |
| 客户时间窗 | 默认宽窗；`tw_tight=True` 时缩到 width=35 | `week06_ground_air_evrp_tw.py::make_instance(tw_tight=...)` |
| 单位约定 | 距离 = 速度 × 时间；服务时间 = 5.0；充电时间 = 40.0 | `SERVICE`、`RECHARGE` 常量 |

合成算例规模：8 / 12 / 16 / 20 客户各 1 实例（单种子 1 个）→ 现在扩到 N=30 / 50（见 §4），并用 10 个种子取均值。

## 2. OR-Tools 求解器（决定性，多种子无意义）

| 脚本 | 关键参数 | 值 | 备注 |
|---|---|---|---|
| `benchmark_official_solomon.py` | `first_solution_strategy` | `PATH_CHEAPEST_ARC` | OR-Tools 决定性算法 |
| 同上 | `local_search_metaheuristic` | `GUIDED_LOCAL_SEARCH` | |
| 同上 | `time_limit.seconds` | 10 | 每实例上界 |
| 同上 | 距离标度 | ×10（按 Solomon 原整数坐标） | 见 `benchmark_official_solomon_output.txt` 头 |
| `benchmark_evrptw.py` / `week04_evrp_tw.py` | 搜索策略 | 纯搜索 + Cheapest Arc | 用 `SetFixedCostOfAllVehicles(大值)` 优先最小化车辆数 |
| 同上 | 时间上界 | 5 s | 6 客户小算例 |

**为什么不给 OR-Tools 多种子**：OR-Tools 求解是决定性算法（除非显式设随机），多跑 N 次只可能因为 `time_limit` 提前终止而出差异；这里都是按时上界跑完的，重复无信息。所以 56 实例的 OR-Tools 数字就是单一确定值（7.2% gap 来自 `benchmark_official_solomon_results.csv`）。

## 3. GA 求解器（**唯一随机、需多种子**）

| 项 | 值 | 出处 |
|---|---|---|
| `POP_SIZE` | 40 | `baseline_ga_vrptw.py` |
| `N_ELITE` | 6 | 同上 |
| `TOURNAMENT` | 4 | 同上 |
| `MUT_RATE` | 0.30 | 同上 |
| `TIME_LIMIT_S` | 8（每实例） | 同上 |
| `penalty` | 1000.0 | `solve_ga` 内：偏离 BKS 车辆数时每车 +1000 |
| 解码 | Solomon I1 风格：每客户插到使总距离增加最小的可行位 | `decode()` |
| 局部搜索 | 2-opt intra-route + relocate inter-route（最多 6 pass） | `local_search()` |
| 初始化种子 | Clarke-Wright savings 构造 → 1 个个体；其逆序 → 第 2 个 | `savings_init()` |
| 车队规模处理 | 偏 BKS；不足时 `force_fleet` 强拆最长路直到达标 | `force_fleet()` |
| **旧 SEED** | `20260717`（单一） | `main()` 顶部 `random.seed(SEED)` |
| **新 SEEDS** | `[20260717, 20260801, 20260815, 20260901, 20261001]`（5 个） | `baseline_ga_vrptw_multi.py` |

**关键改动**：把全局 `random.seed(SEED)` 移到 `solve_ga(data, seed, ...)` 内层，每次重置一次；`main()` 接受 `--seeds 20260717 20260801 ...` 风格（CLI 简化：直接读 `os.environ.get("SEEDS")` 或按需多进程串行）。

## 4. Ground-air / FSTSP 协同实验

| 项 | 值 | 出处 |
|---|---|---|
| `V_T`（卡车速度） | 1.0 | `week06_ground_air_evrp_tw.py` / `week07_fstsp_repro.py` |
| `V_D`（无人机速度） | 2.0 | 同上 |
| `R_D`（无人机航程） | 160.0（ground-air）/ 100.0（FSTSP 模式） | `week06` 中 `R_D`，FSTSP 模式由 `R_D_FSTSP` 调小以触发更多约束 |
| `Q_DEFAULT`（电池容量） | 250 | `week06` |
| 能量消耗 | 1.0 / 距离单位 | `simulate()` |
| `SERVICE` | 5.0 | 同上 |
| `RECHARGE` | 40.0 | 同上 |
| 客户数规模 | 8 / 12 / 16 / 20（10 种子基 `20260720`） | `week06_ground_air_evrp_tw.py::main` |
| **新增规模** | 30 / 50（5 种子，2 配置对比 published vs V2 vs V2+LS） | 新增 N=30/50 实验，见 §4 |
| 单次飞行最多服务客户数 | `max_cust = 2`（改进版可到 3 / 4） | `week07_improvement_ablation.py` |
| 多次起降 | 同停靠点可多次起飞（`multi_takeoff=True`） | 同上 |
| 评估器 | 串行无人机（**重要修正**：不能并行程） | `week07_fstsp_repro.py::fstsp_simulate` |
| 2-opt LS | intra-route 2-opt 改进，**接受条件：makespan 不变差、可行** | 新增 `week07_improvement_ablation.py::v2_with_2opt` |

## 5. 随机种子统一约定

| 用途 | 旧基线 | 新基线 |
|---|---|---|
| GA 种群 | `20260717` 单一 | `20260717/20260801/20260815/20260901/20261001` 5 个，**取均值** |
| 合成算例 | `SEED + n`（8/12/16/20） | `SEED + size_index`（也加 N=30/50 偏移） |
| 多种子 ground-air | `20260720..20260729` 10 个 | 沿用，不再变 |
| FSTSP 同台 | `20260720..20260729` 10 个 | 沿用，但新增 `seed_base=20260820` 跑 N=30/50 |

## 6. 路径与文件约定

- **数据/结果**：`src/results/*.csv`、`src/results/*.txt`、`src/results/*.log`
- **实例缓存**：`src/instances/official_solomon/{C101.vrp, C101.sol, ...}`（首次运行时从 PyVRP/Instances 仓库拉取，已缓存）
- **实验脚本**：`src/experiments/*.py`
- **报告/笔记**：`docs/*.md`（提交仓库）和 `learning_guide/*.md`（自学，**不进提交仓库**）

---

*这一页之后任何脚本改参数都必须回来更新对应行；忘了更新就是回到了"散落在 7 个脚本里"的老问题。*
