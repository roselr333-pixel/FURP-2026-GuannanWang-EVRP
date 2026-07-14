# 论文笔记 1 —— EVRP 综述（打底）

> **基本信息**
> - 引用：Erdelić, T., & Carić, T. (2019). A Survey on the Electric Vehicle Routing Problem: Variants and Solution Approaches. *Journal of Advanced Transportation*, Vol. 2019, Article ID 5075671, 48 pages. https://doi.org/10.1155/2019/5075671（Hindawi，开源 Gold OA）
> - 阅读日期：2026-07-13
> - 说明：本笔记由 AI 辅助整理、本人已于 2026-07-13 通读 PDF 原文后定稿；模板原错引已改正（见下方 ⚠️）。

---

## 1. 这篇在解决什么问题（概览）

> 综述不解决单一问题，而是**分类 + 总结**整个 EVRP 领域。读的时候重点抓：EVRP 有哪些变体？按什么维度分类（车队类型 / 充电模型 / 目标 / 约束）？

- **EVRP 家族分类（我画一棵简单的树）**：
  - EVRP 基础 = VRPTW + 续航（range）限制 + 充电（recharge）事件
  - 按**充电方式**分：
    - Full recharge（到站充满）—— 早期做法（含 Schneider 2014）
    - Partial recharging（只充到够到下一站）—— 更省时省钱、更现实
    - Battery Swap（BSS 换电）—— 几分钟换电池，比最快充电还快
  - 按**充电函数**分：linear / constant（线性或固定时间） vs nonlinear（真实 CC-CV 非线性）
  - 按**车队**分：单一 BEV / 混合车队（电动+传统 ICEV）/ HEV、PHEV
  - 按**站点决策**分：CS 位置给定 vs 同时选址（E-LRP，electric location-routing）
  - **相关但不同**的问题：两层级路径（2E-VRP）、绿/污染路径、动态交通、多目标
- **文中提到的"主流方法"有哪些（精确 / 启发式 / 元启发式 / 学习）**：
  - 精确：MIP、branch-price-and-cut、dynamic programming（RCSPP）、set partitioning
  - 启发式：构造启发（constructive）+ 改进启发（improvement / local search）
  - 混合元启发：**ALNS**（adaptive large neighborhood search，Schiffer & Walther [88]）、**混合遗传算法**（Hiermann et al. [96]）被点名"produced high-quality solutions"
  - 学习类：本文（2019）基本未涉及 ML/RL 求解，属于当时空白
- **开放问题（open challenges）里哪几条和我项目相关**：
  - 非线性充电被长期忽视 → 忽略它"会导致不可行解和额外惩罚成本"（§4.13）
  - CS 容量/等待/预约（capacitated stations、reservations）研究很少
  - 动态交通与不确定性（需求、行程时间、时间窗、服务时间、充电时间）研究不足
  - 缺少真实案例研究（case studies），模型多在合成算例上验证

## 2. 核心方法（综述视角）

- **充电模型分几类（线性 / 非线性 / 部分充电 / 换电）**：
  - **Full recharge + 线性/常数充电**（文中 34 篇用线性充电函数）：最简单，充电时间固定或随电量线性；但忽略真实电池非线性
  - **Partial recharging（30 篇）**：只充到能完成下一段（到下一站或 depot），可删掉冗余 CS、车辆空电回 depot；经济上更优
  - **Nonlinear charging（仅 8 篇）**：真实锂电池 CC-CV（先恒流到 ~80%，后恒压指数放缓）；Montoya 等指出忽略非线性会让 12% 的好解落在非线性段 → 解不可行或偏贵
  - **Battery Swap / BSS（9 篇）**：换电池 <10 分钟，比最快充电还快，且可在夜间低谷电价充
  - **不同充电技术（17 篇）**：慢(3kW)/快(7–43kW)/rapid(50–250kW)，按时间窗松紧选最优；没有单一技术占优，联合技术最好
- **时间窗、容量、电池这几个约束通常是怎么耦合的**：
  - 三维耦合：负载（容量）+ 时间窗 + 电池（能量/SoC）
  - 电池维度靠"进站重充"事件衔接——在 CS 节点把 SoC 补回
  - 目标通常**分层**：先 min 车辆数、再 min 里程（§2 末尾）。因为 BEV 购置贵，少车优先，这点我代码里已经做对了
  - 可行性处理两派：只允许可行解 vs 允许不可行解（带惩罚项 𝑓=𝑓_dist+𝛼P_cap+𝛽P_tw+𝛾P_batt），搜索后期逐步加大惩罚

## 3. 对我项目的可复用点

- **我的 EVRP-TW（第4周）充电用的是"负电量"取巧建模，综述里哪种充电模型是"标准"做法？我该往哪靠**：
  - 我的"进充电站 → 电量 +电池容量"属于 **full recharge（充满）+ 线性/常数充电时间** 的简化假设，正是 Schneider 2014 E-VRPTW 的早期做法（§4.4 开头点名 [25] 用 full recharge）
  - 标准更优做法是 **partial recharging**（只充够到下一段），更省时省钱、更现实
  - 我代码把充电时间当成近似 0 / 固定，对应 §4.6 的"linear or constant charging time"简化；真实应是非线性 CC-CV
  - ⇒ 下一步可拓展方向：① 改 partial recharging；② 引入分段线性的非线性充电函数
- **我的卡车-无人机 v2 在综述的分类里属于哪一类**：
  - 这篇是**纯电动车辆综述，不覆盖卡车-无人机（FSTSP / Murray & Chu 2015）**，不在它的 taxonomy 内
  - 我的 v2（任意节点起降）属于 "truck-drone / vehicle routing with auxiliary drone" 家族，要等读 Murray & Chu 2015 来定位
  - 但**如果把"电动"引入 truck-drone**（电动卡车+无人机），就会和本文的 §3.2 能耗模型（LDM）+ §4.4/§4.6 充电建模结合——这是未来值得做的交叉方向，目前文献也很少

## 4. 复现成本评估

- 综述本身无需复现；但它指向的**"必读方法论文"**是哪几篇（记下来，作为后续阅读候选）：
  - **Schneider, Stenger & Goeke (2014) E-VRPTW 奠基（ALNS）** —— 我的主问题底座，下一篇就读它
  - **Schiffer & Walther (2018) [88]** ALNS + 附录 destroy/repair 算子 —— 被综述点名高质量解，附录是算子清单
  - **Hiermann et al. (2019) [96]** 混合车队 E-VRP + 混合 GA —— 异构车队参考
  - **Montoya et al. (2017) [72]** 非线性充电 E-VRP-NL —— 想做 CC-CV 时参考
  - **（后续）Murray & Chu (2015) FSTSP** —— 我的 truck-drone 源头，单独读

## 5. 我的疑问 / 待深挖

- 我的能耗 `RegisterTransitCallback` 是按**距离线性**算的，还是考虑了载重/坡度？若是前者，按 §3.2 误差可达 **70%**，要不要改成 load-aware（Goeke & Schneider 模型）？
- **Partial recharging** 在我的 OR-Tools 框架里怎么建模？电量维度允许充到"刚好够到下一段"而不是充满，slack 上限该怎么设？
- 非线性 **CC-CV** 怎么在 MILP / OR-Tools 里做分段线性化（piecewise-linear concave）？
- 把"电动"加进 truck-drone：无人机航程 + 卡车电量 + 会合约束，三者怎么在同一模型里耦合？
- 综述说 **ALNS** 是 E-VRP 的高质量解法——我目前用 OR-Tools（构造+GLS），和 ALNS 的差距本质在哪？要不要自己实现一个 ALNS 作为基线对比？

## 6. 一句话总结（elevator pitch，写给我自己）

> EVRP 就是在经典 VRP 上加了"电量"这一个维度，所有难点都来自**续航有限 → 必须充电 → 充电又耗时间且非线性**；这篇综述给了我一张全局地图，也让我看清自己 E-VRPTW 的"充满 + 线性充电"只是最简化假设，下一步该往 **partial recharging** 和 **nonlinear charging** 靠，而 truck-drone 部分要另读 Murray & Chu 2015。
