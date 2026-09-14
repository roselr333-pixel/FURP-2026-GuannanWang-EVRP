# 本轮工作记录（2026-09-13）

这份文件按主题记录这一轮对仓库做的改动、怎么验证、以及还没做完的部分，方便和 `git log` 对照。
提交号都是本地/远端 `master` 上的真实提交。

## 1. 总览

这一轮从"整理文件 + 检查 bug"开始，做到的研究清单是：**主线搬标准算例 → Schneider 2014 复现补局部搜索 → 启用/研究卡车载重 → 无人机能耗/载荷接进 V3 与 W8 → 精确最优性边界**。
期间还修掉了评估器的一类物理性缺陷、统一了产物编码、补了两组回归测试（现共 151 个），并把文档、图、`run_all.py` 与证据索引全部同步。

## 2. 按主题

### 2.1 评估器物理化并全量重跑（`72055fb`、`09b9706`）

- `week07_fstsp_repro.fstsp_simulate` / `fstsp_simulate_multi` 与 `week06_ground_air_evrp_tw.simulate` 原先允许"嵌套/交叉架次"（无人机还在飞上一架次就能从后面的卡车节点起飞），会把不可实现的计划算出一个偏低的 makespan。现在统一强制：发射点在回收点之前、飞行 ≤ `R_D`、发射时无人机必须已回到卡车，任一条不满足即返回 `inf`。
- 依赖这些评估器的实验（week06/07/08、V3）全部重跑，日志与图重新生成；旧的单架数字（如 56.7%~87.8%）因此被更正。
- 记录在 `docs/analysis/evaluator_physical_fix_note_zh.md` / `_en.md`，失败案例表里的 FC-7-2/7-3/7-4。

### 2.2 精确最优性量化（`bc9411d`，本轮加强为 `5897a98`）

- `cpsat_fstsp.py`：物理评估器 + 干净贪心 + CP-SAT 精确模型（弧 + MTZ 位序 + 显式枚举候选架次 + 单架"在空"状态链），用 `1/SC`（`SC=100`）离散时间；两项独立验证（航程=0 退化为 TSP 对 Held-Karp；n=5 对全空间暴力枚举）。
- 本轮新增热启动：`solve_exact(..., upper_bound=..., hint=(route, trips))`，提示通过 `AddHint` 落在路线弧、MTZ 位序、卡车/无人机归属与选中的架次上，并返回认证对偶界。
- `week08_exact_gap.py` 扩到 **n=8/10/12/14/16 × 5 种子**（n=8 给 120 s，其余 60 s）。
- 结果：n=8 **5/5 证明最优**（贪心 +31.2%、LNS +16.5%，与冷启动逐值一致）；冷启动在 n=12 可能连可行解都拿不到，热启动后 25 个实例里 23 个拿到计划；**从 n=10 起 CP-SAT 自己的可行计划比我的贪心/LNS 再好 8.8~17.5%**，但认证对偶界在 n≥10 全为 `0.0`（另做 300 s / 16 workers 探针在 n=10 也只有 27.6 对 217）——最优性证不出的瓶颈在松弛，不在时间。
- 图 `figures/exact_gap.png` 改成两栏（启发式 gap + primal vs dual）。

### 2.3 文档整理与格式（`700ffaf`、`48b71bf`、`b680fed`）

- `docs/` 按用途分成 `reference/ analysis/ weekly/ baselines/`，加 `docs/README.md` 索引；补形式化建模文档（`formal_model_zh.md` / `_en.md`，中英各自独立成文）。
- 全文改成第一人称、去掉带日期的状态标注，只保留"写成什么样、下一步做什么"的直接说明。
- `docs/reference/configs_and_parameters.md` 重写：常量、算例来源、每个实验脚本的规模/种子/参数、求解器参数、路径约定逐项列清并标出处；同步修正 week07 正文里的旧数字。

### 2.4 核心消融扩展（`551c6a8`、`94f5757`）

- `week07_ablation_std.py`：把五配置消融搬到官方 Solomon 拓扑（4 族 × 3 顾客窗口 × N=8/12/16/20 = 48 个实例），多顾客增益 +7.2~8.9pp，与合成结论一致。
- `v3_ablation.py`：同一套消融搬到 V3（电动卡车 + 充电站 + 时间窗 + 无人机），多顾客 +8.5~12.5pp 仍是主增益，N=20 转为 −2.8pp。

### 2.5 无人机能耗/载荷模型（`88d1f11`，本轮接入主线 `bcffefd`）

- `drone_energy.py`：给无人机加载荷上限 `P_MAX` 与随机上剩余载重增长的能耗预算 `E_D`，`BETA=0` 且 `E_D=R_D` 时精确退化为原航程模型（300 个随机计划逐值比对，0 处不一致）。
- `drone_energy_ablation.py`：能耗模型下重跑核心消融——多顾客增益 +10.4 → +6.1pp（BETA 0→0.04），不感知能耗的已发表启发式只有 42~48% 计划可行。
- 本轮把同一套闸门（`alpha`/`beta`/`ed`/`p_max`）装进 `v3_ev_collab.ev_collab_k` 与 `week07_fstsp_repro.fstsp_simulate[_multi]`，`drone_energy_mainline.py` 在 V3 与 W8（K=1/2/3）上开闸门重跑：BETA=0 一行与已提交结果 `max|diff| = 0.000`；收益仍在（V3 K=1 33.5→53.0%、K=3 到 72.4%；W8 K=3 51.2→70.6%），代价是 makespan 多 1.5~8.1%，N≥16 时"多一架"的边际价值少 5~10pp，返回计划 100% 可行。

### 2.6 Bug 审计（`bcb8612`、`ccae21c`）

- 修：CP-SAT 自检用固定 `1e-6` 比较 `1/SC` 离散目标导致偶发失败；OR-Tools 求解器参数名过期（`PATH_CHEAPEST_ARC` → `PARALLEL_CHEAPEST_INSERTION`）并更正"可复现"的说法（56 实例均值 7.2%~8.1% 浮动）；中文乱码/编码不统一（34 个脚本统一 `encoding="utf-8"`）；死代码与命名（`mc_tsp`、`DEPOSIT`→`DEPOT`）；16 处未使用解包改名。
- 三基线（OR-Tools / PyVRP / 自写 GA）与 week06–08 的入口逐个自检、跨模块一致性核对，补/更新回归测试。

### 2.7 README 与复现入口（`4cc800c`）

- README 增加"五分钟导览"和"哪张图回答什么问题"表；`run_all.py` 扩到覆盖全部实验与绘图脚本（现 45 步，全部路径可解析）。
- `REPRODUCE.md`：每条结论 → 脚本 → 产物对照，图 → 生成脚本对照。

### 2.8 卡车载重（`4e60939`）

- 启用 `CAP=1000`（`truck_ev_route` / `simulate` 检查路线承载需求之和，超载判 `cap_inf`，V2 卸载顾客时需求随之离开卡车并在贪心里先"修"超载）。
- `week06_capacity_study.py`：7 规模 × 5 种子 × cap ∈ {1000, 600, 400}。结果：声明值对 N≤50 不 binding，N=100 有 1/5 算例 binding（需求 1081）；cap=600 在 N=100 全 binding、cap=400 在 N≥50 全 binding，而单架串行无人机最多卸掉约 10~20% 的需求，修不回来；载重与能耗是两道独立的门（N=100 的 V1/V2 能量可行性 0/5）。图 `figures/capacity_binding.png`。

### 2.9 主线搬到标准算例（`4a0396d`）

- `std_evrp_instances.py`（Schneider 2014 原始数据的适配器）+ `week06_standard_instances.py`：6 族 × 4 个子集 × N=8/12/16/20，两种载重口径。
- 结果：协同增益 **41.0~54.8%**，比合成算例的 24.8~34.5% 更大，说明合成结论偏保守；迟到顾客从 5.17/8.79/12.71/16.96 降到 0.96/2.92/4.96/7.71；论文自己的 C=200 在 4 个规模上分别 binding 0/24、7/24、12/24、12/24。图 `figures/std_instances.png`。

### 2.10 Schneider (2014) E-VRPTW 复现（`0b25288`）

- `schneider_evrptw.py` + 新增 `schneider_improve.py`：92 个原始实例全部可解，18 个有 BKS 的实例平均距离差距 **+52.7%（构造）→ +21.3%（加局部搜索）**，车辆数 5.44 → 3.28（BKS 2.06），c208C5 / r105C5 / rc208C5 精确命中 BKS。
- 过程中修了两个真 bug：局部搜索里"同一辆车被触碰两次"导致车辆重复；新车辆首趟行程未校验车场关闭时间。补 17 个求解器回归测试。
- 复现说明 `docs/baselines/schneider_evrptw_replication_zh.md` / `_en.md`；图 `figures/schneider_routes.png`、`schneider_vehcomp.png`。

## 3. 现在的验证状态

| 项目 | 结果 |
|---|---|
| `pytest tests/ -q` | **151 passed**（约 20~30 s；`tests/test_cpsat_exact.py` 的 CP-SAT 校验占大头） |
| `pyflakes src tests run_all.py` | 无告警 |
| 文档引用检查（`docs/` 内路径） | 111 条，悬空 0 |
| `run_all.py` 步骤路径 | 45 步，全部存在 |
| 产物编码 | `src/results` 下文本产物全部 UTF-8（本轮把两份被 PowerShell `Tee-Object` 写成 UTF-16 的运行日志改回 UTF-8） |

## 4. 还没做的

- **W6–W8 的周记**：`docs/weekly/0-5_weekly.md` 只覆盖第 1–5 周。W6/W7/W8 目前只有"按实验"的说明（`week06_ground_air_report`、`week07_*`、`week08_*`），没有按周归档的 checkpoint。
- **Schneider (2014) 的阅读笔记**：复现本身已经做完，缺的是论文笔记（拿不到 PDF）。
- **报告 / 海报 / 演示视频**：占评分约 30%，目前还没开始；任务书截止 2026-09-15。
- **精确最优的更强下界**：n≥10 的对偶界目前是 0，需要换松弛（对架次集合做列生成或拉格朗日界）才谈得上"证明最优"。
- **更强的元启发式**：从 n=10 起 CP-SAT 的可行解比我的贪心/LNS 再好 8.8~17.5%，说明搜索一侧还有空间（ALNS / ruin-and-recreate）。
- **侧线**：`src/results/baseline_ga_run.log`、`baseline_pyvrp_run.log` 目前没有对应的生成脚本（当时是手动 tee 的），要么补脚本，要么在文档里说明来源。

## 5. 怎么验证这一轮的东西

```bash
python -m pytest tests/ -q            # 151 个回归测试
python run_all.py                     # 一键重跑全部实验与图（约 2~2.5 小时，GA 与两个能耗扫描最慢）

# 单独重跑本轮的两组实验：
python src/experiments/drone_energy_mainline.py   # V3 与 W8 开能耗/载荷闸门
python src/experiments/week08_exact_gap.py        # CP-SAT 热启动，含证明边界
python src/tools/gen_drone_energy_mainline_figure.py
python src/tools/plot_exact_gap.py
```

结果 CSV 按 `.gitignore` 不入库（脚本 + 固定种子可重新生成），日志入仓；脚本在日志头部打印运行机硬件与 Python 版本，raw CSV 里逐实例记录 `runtime_s`。
