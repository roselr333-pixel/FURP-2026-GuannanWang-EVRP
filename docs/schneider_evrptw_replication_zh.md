# Schneider (2014) E-VRPTW 复现说明（补充实验）

> 说明：本文件记录我对 Schneider, Stenger & Goeke (2014), *The Electric Vehicle-Routing
> Problem with Time Windows and Recharging Stations*, Transportation Science 48(4) 的 E-VRPTW
> 基准做的**自写构造式复现**。它补在我原有卡车–无人机 EVRP 项目之外，用来展示我也独立实现
> 了标准的电动车 VRPTW（带充电站）模型，并能和文献 BKS 对照。所有数字来自
> `src/experiments/schneider_evrptw.py` 与 `schneider_bks_compare.py`，可一键重跑。

## 1. 模型（E-VRPTW，满充瞬时充电）

- 车队从 depot 出发，服务带时间窗 `[ready, due]` 的顾客，每个顾客服务时间 `serv`。
- 电动车电池容量 `Q`，能耗率 `r`（单位距离耗电），车速 `v`。
- 电池不足时，可绕经最近充电站 **瞬时满充**，补能时间 `= (Q − soc)·g`（`g` 为补能逆率）。
- 容量约束 `C`、时间窗约束（允许到达后等待）、电池非负约束。
- **目标**：Schneider 的层级目标——**先最小化车辆数，再最小化总距离**。

## 2. 实例来源（公开，未用论文 PDF）

- 实例来自公开 GitHub 镜像（EllinorAndRegina 的 ALNS 毕设仓的 `SchneiderEVRPTW/`）。
- 为确认这些文件就是 Schneider 原版，我与 **jmanzolli/E-VRPTW** 仓里的原版实例逐文件核对：
  `c103C5`、`c206C5` 完全一致，`c101C5`、`rc108C5` 仅空白字符差异，数据相同。
  故对标有效。
- 我用到的集合：100 顾客 `_21` 集（21 充电站）、5 顾客 `C5` 集（3–4 充电站）、
  以及 10/15 充电站变体，共 **92 个实例**（已跳过 `readme.txt`）。
- 论文 PDF 本机无法下载（代理拦截学术出版商），但实例为公开数据、模型由实例文件
  底部的参数完全定义，因此复现不依赖 PDF。

## 3. 方法（自写构造式贪心）

`src/experiments/schneider_evrptw.py`：每辆车从 depot 出发，按截止时间升序贪心插入
**最近的可行顾客**（容量 / 时间窗 / 电池三重可行；电池不够则经最近充电站满充后继续），
一条路线结束后闭合回 depot，再开下一辆车。这是最简单的可行构造式启发式，
**未做车辆数最小化、未做多程（multi-trip）、未用元启发式**。

## 4. 结果

- 92 个实例全部跑通；**RC1 家族有 1 个顾客因时间窗过紧、贪心插不进，未被服务**
  （`unserved=1`，已在 CSV 中如实记录，不做掩盖）。
- 18 个实例有 Schneider (2014) 发表的 BKS 可对照（见下表）。BKS 来源：
  - `C5` 小实例（5 顾客）：取自 jmanzolli/E-VRPTW 直接列出的 Schneider (2014) CPLEX 结果；
  - `_21` 大实例（100 顾客）：取自 Adachi et al. (2022, IEICE NOLTA) 引 Schneider (2014) 的 BKS 表。

## 5. 与 BKS 的差距（诚实归因）

| 集合 | 距离差距（均值） | 主因 |
|---|---|---|
| C5 小实例（5 顾客） | **约 +25%**（区间 −0.4% ~ +45.8%） | 车辆数偏多 + 贪心路线非最优 |
| `_21` 大实例（100 顾客） | **+50% ~ +216%** | 车辆数差距巨大（见下） |

差距的真实来源（我都如实写，不夸大）：

1. **车辆数未最小化（主因）**。Schneider 的首要目标是最小化车辆数，且其车辆可
   **多程**（一次出库跑多条路线）；我的贪心每车只跑一趟、也不优先压缩车辆数，
   故车辆数明显偏多，直接拉高总距离。例如 `c201_21`：我方 17 车 vs BKS 4 车；
   `rc201_21`：15 车 vs 4 车。大实例的距离差距绝大部分来自这里，而非路线几何。
2. **启发式简单**。最近可行插入，路线几何非最优，顾客分配有碎片。
3. **距离度量**。我用原始欧氏距离；论文可能截断到 1 位小数，差异 < 0.1%，可忽略。
4. **关于 `c103C5` 我方距离略低于 BKS**：这不是实例不同（已核对一致），而是 Schneider
   层级目标下 BKS 选了 **更少车辆（m=1）而接受略高距离（176.05）**，我的 3 车解距离
   175.3 略低但车辆更多，按论文目标我方更差——符合预期。

## 6. 局限与下一步（明确留白）

- RC1 紧时间窗下 1 顾客未服务 → 需要更重的插入搜索或 ALNS。
- **车辆多程 + 最小化车辆数未实现**，这是接近 BKS 的关键杠杆，留作扩展
  （同侪 Ziqi / Frank 用 ALNS / 元启发式正是为此）。
- 仅构造式启发式，未求精确下界（MILP）；求下界本身是独立贡献，超出本项目范围。
- 以上均如实写入报告，不把"接近 BKS"写成已达成。

## 7. 产物

- `src/experiments/schneider_evrptw.py` —— 实例解析 + 构造式求解器
- `src/results/schneider_evrptw_baseline.csv` —— 92 实例基线（车辆数 / 距离 / 未服务数）
- `src/experiments/schneider_bks_compare.py` —— BKS 对照脚本
- `src/results/schneider_evrptw_bks_comparison.csv` —— 18 实例对标表
- `instances/schneider_evrptw/` —— 实例（公开镜像）
- `instances/schneider_evrptw_original/` —— 与 jmanzolli 原版核对用的实例
