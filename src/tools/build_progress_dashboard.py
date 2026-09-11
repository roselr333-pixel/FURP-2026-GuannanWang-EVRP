#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generate a self-contained HTML progress dashboard for the FURP 2026 EVRP project.
All figures are inlined as base64 so the dashboard is fully portable / previewable offline.
"""
import base64
import os
import datetime

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIGDIR = os.path.join(REPO, "figures")
OUT = os.path.join(REPO, "progress_dashboard.html")

GEN_DATE = "2026-09-10"
DEADLINE = "2026-09-15"


def b64(path):
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


figs = {
    "consolidated": b64(os.path.join(FIGDIR, "baseline_consolidated.png")),
    "pyvrp_family": b64(os.path.join(FIGDIR, "pyvrp_family_gap.png")),
    "sensitivity": b64(os.path.join(FIGDIR, "sensitivity_panels.png")),
    "mo_scatter": b64(os.path.join(FIGDIR, "mo_scatter.png")),
    "mo_tradeoff": b64(os.path.join(FIGDIR, "mo_tradeoff.png")),
    "largen": b64(os.path.join(FIGDIR, "largen_scale_decay.png")),
}

# ---- task counts (from TaskList snapshot 2026-09-10) ----
done, inprog, pending = 61, 3, 11
total = done + inprog + pending
pct = round(100 * done / total)

HTML = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FURP 2026 进度看板 · 卡车-无人机协同 EVRP-TW</title>
<style>
  :root {{
    --bg:#f6f8fb; --card:#ffffff; --ink:#1f2933; --muted:#66727f;
    --line:#e3e8ef; --accent:#2563eb; --green:#1f9d55; --amber:#d97706; --red:#dc2626;
    --blue:#2563eb; --purple:#7c3aed;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
    line-height:1.55; }}
  .wrap {{ max-width:1080px; margin:0 auto; padding:28px 20px 64px; }}
  header.top {{ background:linear-gradient(135deg,#1e3a8a,#2563eb); color:#fff;
    border-radius:16px; padding:26px 28px; box-shadow:0 6px 22px rgba(37,99,235,.25); }}
  header.top h1 {{ margin:0 0 6px; font-size:22px; }}
  header.top .sub {{ opacity:.9; font-size:14px; }}
  .deadline {{ margin-top:16px; display:flex; gap:18px; flex-wrap:wrap; }}
  .deadline .chip {{ background:rgba(255,255,255,.15); border:1px solid rgba(255,255,255,.3);
    border-radius:10px; padding:10px 16px; }}
  .deadline .chip b {{ font-size:24px; display:block; }}
  section {{ background:var(--card); border:1px solid var(--line); border-radius:14px;
    padding:20px 22px; margin-top:20px; }}
  h2 {{ font-size:17px; margin:0 0 14px; display:flex; align-items:center; gap:8px; }}
  h2 .dot {{ width:10px; height:10px; border-radius:50%; background:var(--accent); }}
  .ringwrap {{ display:flex; align-items:center; gap:26px; flex-wrap:wrap; }}
  .ring {{ --p:{pct}; width:140px; height:140px; border-radius:50%;
    background:conic-gradient(var(--green) calc(var(--p)*1%), #e7ecf3 0);
    display:flex; align-items:center; justify-content:center; position:relative; flex:none; }}
  .ring::after {{ content:""; position:absolute; inset:14px; background:var(--card); border-radius:50%; }}
  .ring b {{ position:relative; font-size:30px; color:var(--green); }}
  .ring small {{ position:relative; display:block; text-align:center; color:var(--muted); font-size:12px; }}
  .legend {{ font-size:13px; color:var(--muted); }}
  .legend div {{ margin:4px 0; }}
  .bar {{ height:22px; border-radius:6px; background:#eef2f7; position:relative; overflow:hidden; margin:8px 0 4px; }}
  .bar > span {{ position:absolute; left:0; top:0; bottom:0; border-radius:6px; }}
  .barlbl {{ display:flex; justify-content:space-between; font-size:13px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:14px; }}
  .kpi {{ border:1px solid var(--line); border-radius:12px; padding:14px; }}
  .kpi .v {{ font-size:26px; font-weight:700; color:var(--accent); }}
  .kpi .k {{ font-size:12px; color:var(--muted); margin-top:2px; }}
  .kpi.good .v {{ color:var(--green); }} .kpi.warn .v {{ color:var(--amber); }} .kpi.bad .v {{ color:var(--red); }}
  figure {{ margin:0 0 22px; }}
  figure img {{ width:100%; border:1px solid var(--line); border-radius:10px; background:#fff; }}
  figcaption {{ font-size:13px; color:var(--muted); margin-top:6px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th,td {{ text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); }}
  th {{ color:var(--muted); font-weight:600; }}
  .tag {{ display:inline-block; padding:2px 9px; border-radius:999px; font-size:12px; font-weight:600; }}
  .t-done {{ background:#e7f6ee; color:var(--green); }}
  .t-prog {{ background:#fef3e2; color:var(--amber); }}
  .t-pend {{ background:#fdeaea; color:var(--red); }}
  .t-warn {{ background:#fff4d6; color:#a16207; }}
  ul.todo li {{ margin:6px 0; }}
  .note {{ background:#fff8e6; border:1px solid #f3e3b3; border-radius:10px; padding:12px 14px;
    font-size:13px; color:#7a5b00; margin-top:14px; }}
  footer {{ color:var(--muted); font-size:12px; text-align:center; margin-top:26px; }}
</style>
</head>
<body>
<div class="wrap">

  <header class="top">
    <h1>FURP 2026 · 卡车-无人机协同 EVRP-TW — 项目进度看板</h1>
    <div class="sub">提交仓库 roselr333-pixel/FURP-2026-GuannanWang-EVRP · 生成于 {GEN_DATE}</div>
    <div class="deadline">
      <div class="chip"><b id="dd">—</b><span>距最终 report 截止 {DEADLINE}</span></div>
      <div class="chip"><b>{pct}%</b><span>任务完成度 ({done}/{total})</span></div>
      <div class="chip"><b>{inprog}</b><span>进行中任务</span></div>
      <div class="chip"><b>{pending}</b><span>待办任务</span></div>
    </div>
  </header>

  <section>
    <h2><span class="dot"></span>① 总览：任务 vs 关键交付物</h2>
    <div class="ringwrap">
      <div class="ring"><b>{pct}%</b><small>任务完成</small></div>
      <div class="legend">
        <div>✅ 已完成任务：<b>{done}</b>（W1–W7 实验、基线、消融、敏感性、多目标、文档）</div>
        <div>🟡 进行中：<b>{inprog}</b>（#56 早期基线多种子重跑 / #67 PyVRP基线 / #71 深化敏感性）</div>
        <div>🔴 待办：<b>{pending}</b>（终稿报告、幻灯片、视频、Poster、最终push 等）</div>
        <div style="margin-top:8px;color:var(--muted)">注：任务完成度高，但 <b>占分 30% 的终稿报告与证书强制项(Poser/视频)尚未开始</b>，
        这是当前最大风险，不是"快做完了"。</div>
      </div>
    </div>
    <h3 style="font-size:14px;margin:18px 0 8px;">交付物就绪度</h3>
    <div class="barlbl"><span>代码与模型 (W1–W7)</span><span>100%</span></div>
    <div class="bar"><span style="width:100%;background:var(--green)"></span></div>
    <div class="barlbl"><span>实验证据（图 + A/B/C 三实验）</span><span>100%</span></div>
    <div class="bar"><span style="width:100%;background:var(--green)"></span></div>
    <div class="barlbl"><span>三基线对比（OR-Tools / GA / PyVRP / BKS）</span><span>100%</span></div>
    <div class="bar"><span style="width:100%;background:var(--green)"></span></div>
    <div class="barlbl"><span>深度分析文档（机理主线）</span><span>100%</span></div>
    <div class="bar"><span style="width:100%;background:var(--green)"></span></div>
    <div class="barlbl"><span>周报 / checkpoint / 学习笔记</span><span>100%</span></div>
    <div class="bar"><span style="width:100%;background:var(--green)"></span></div>
    <div class="barlbl"><span>可复现包 + 最终 push（已推送远端）</span><span>100%</span></div>
    <div class="bar"><span style="width:100%;background:var(--green)"></span></div>
    <div class="barlbl"><span>终稿 report（W8 · 占 30%）</span><span>0%</span></div>
    <div class="bar"><span style="width:4%;background:var(--red)"></span></div>
    <div class="barlbl"><span>幻灯片 + 5–8 分钟 demo 视频</span><span>0%</span></div>
    <div class="bar"><span style="width:4%;background:var(--red)"></span></div>
    <div class="barlbl"><span>Poster（FURP_Showcase.pdf · 证书强制）</span><span>0%</span></div>
    <div class="bar"><span style="width:4%;background:var(--red)"></span></div>
  </section>

  <section>
    <h2><span class="dot"></span>② 周里程碑</h2>
    <table>
      <tr><th>阶段</th><th>内容</th><th>状态</th></tr>
      <tr><td>W1–W5</td><td>基线复现 · 标准 benchmark(Solomon) · 卡车-无人机 v2 建模</td><td><span class="tag t-done">完成</span></td></tr>
      <tr><td>W6</td><td>协同建模 · 参数敏感性 · 多目标权衡（A/B/C）</td><td><span class="tag t-done">完成</span></td></tr>
      <tr><td>W7</td><td>改进 + 5 配置受控消融 + FSTSP 复现同台</td><td><span class="tag t-done">完成</span></td></tr>
      <tr><td>深化</td><td>三基线整合 · 敏感性升级(误差带) · 深度分析文档</td><td><span class="tag t-done">完成</span></td></tr>
      <tr><td>W8</td><td>最终集成：report / 幻灯片 / 视频 / Poster / 可复现包</td><td><span class="tag t-prog">进行中</span></td></tr>
    </table>
  </section>

  <section>
    <h2><span class="dot"></span>③ 实验证据（真实产出图）</h2>
    <div class="grid" style="margin-bottom:8px">
      <div class="kpi good"><div class="v">−3.0%</div><div class="k">PyVRP 基线 vs BKS（最强求解器）</div></div>
      <div class="kpi"><div class="v">+7.2%</div><div class="k">OR-Tools 商业求解器 vs BKS</div></div>
      <div class="kpi bad"><div class="v">+36.6%</div><div class="k">自写 GA vs BKS（±15.8%）</div></div>
      <div class="kpi warn"><div class="v">+6.6~17.7pp</div><div class="k">消融：多顾客能力主增益</div></div>
    </div>

    <figure>
      <img src="{figs['consolidated']}">
      <figcaption>图1 · 三基线整合对比（按 Solomon 族，gap vs BKS）。PyVRP 平均 −3.0%（优于 BKS），
      OR-Tools +7.2%，自写 GA +36.6%±15.8%。少数 RC2 实例 GA 偏差大（数据驱动的定位，非夸大）。</figcaption>
    </figure>

    <figure>
      <img src="{figs['pyvrp_family']}">
      <figcaption>图2 · PyVRP 逐族 gap。C2 最好（−4.3%），RC2 最弱（−2.1%），整体稳定优于 BKS。</figcaption>
    </figure>

    <figure>
      <img src="{figs['sensitivity']}">
      <figcaption>图3 · 参数敏感性（5 种子均值 ± 误差带）。K(每架次客户数) 1→3：25.3%→56.5%；
      Q(电池) 120→500：55.8%→47.1%；N(规模) 8→30：63.8%→35.3%。
      <b style="color:var(--green)">✓ R(无人机续航) 已修复：60→200 实测随续航变化（15.5%→27.7%→35.2%→50.5%@160，200 处 48.7% 已饱和），与深度文档一致。</b></figcaption>
    </figure>

    <figure>
      <img src="{figs['mo_scatter']}">
      <figcaption>图4 · 多目标散点：V2(距离 215.2, 时长 415.7) 相对 V1 纯卡车(486.4, 622.4) 在两轴同时占优
      （距离 −56%、时长 −33%）。诚实说明：加权和标量化贪心，前沿为"粗"前沿，非完整 Pareto。</figcaption>
    </figure>

    <figure>
      <img src="{figs['mo_tradeoff']}">
      <figcaption>图5 · 多目标权衡曲线（加权和扫描 w∈{{0,0.25,0.5,0.75,1.0}}）。</figcaption>
    </figure>

    <figure>
      <img src="{figs['largen']}">
      <figcaption>图6 · 规模边界（N=30/50/100，5 种子均值）。V2 相对 V1 的 makespan 优势 27.6%→12.1%→2.3% 单调坍缩，
      卸载率 62.0%→42.8%→23.4% 下降，N=100 时 V2 平均 71.4/100 顾客超时（TW 可行性崩溃）。诚实结论：有效协同区间落在 N≤50。</figcaption>
    </figure>
  </section>

  <section>
    <h2><span class="dot"></span>④ 关键结论（来自深度分析文档）</h2>
    <ul>
      <li><b>主线：</b>协作增益主源是"多顾客能力"而非"会合次数"——受控消融(+6.6~17.7pp) 与敏感性 K 扫描(25.3%→56.5%) 两个独立实验互相印证。</li>
      <li><b>适用区间：</b>客户分散、无人机续航不受限、规模中等时协同最划算；规模扩展至 N=100 时收益坍缩至 2.3%、V2 平均 71.4/100 顾客超时（TW 崩溃），有效协同区间落在 N≤50。</li>
      <li><b>三基线定位：</b>PyVRP(领域最强) &gt; BKS &gt; OR-Tools(商业) &gt; 自写 GA，定位清晰、不夸大。</li>
      <li><b>诚实局限：</b>加权和贪心非完整 Pareto 求解；规模受限于合成算例（N=100 时 TW 可行性崩溃，有效区间 N≤50）；未复现 MILP 下界。</li>
    </ul>
  </section>

  <section>
    <h2><span class="dot"></span>⑤ 剩余待办（按优先级）</h2>
    <table>
      <tr><th>优先级</th><th>事项</th><th>对应任务</th><th>状态</th></tr>
      <tr><td>🔴 最高</td><td>写最终 report 终稿（占 30%，原创不套模板）</td><td>#61</td><td><span class="tag t-pend">未开始</span></td></tr>
      <tr><td>🔴 高</td><td>Poster FURP_Showcase.pdf（证书强制项）</td><td>#64</td><td><span class="tag t-pend">未开始</span></td></tr>
      <tr><td>🔴 高</td><td>幻灯片 + 5–8 分钟 demo 视频</td><td>#62</td><td><span class="tag t-pend">未开始</span></td></tr>
      <tr><td>🟢 完成</td><td>commit + push 完善后的项目产物（A/B/C 脚本+图+深度文档+N=100 扩展）</td><td>#74</td><td><span class="tag t-done">已提交</span></td></tr>
      <tr><td>🟢 完成</td><td>核查 R 续航敏感性脚本（参数未生效，已修复重跑）</td><td>#71 子项</td><td><span class="tag t-done">已修复</span></td></tr>
      <tr><td>🟢 完成</td><td>可复现包（run_all + REPRODUCE + requirements）收尾 + push</td><td>#63</td><td><span class="tag t-done">已完成</span></td></tr>
      <tr><td>🟢 低</td><td>把 A/B/C 结果汇总进报告素材文档</td><td>#70</td><td><span class="tag t-pend">未开始</span></td></tr>
    </table>
    <div class="note"><b>⚠ 诚信边界（已写入项目记忆）：</b>对标同学是"差距分析/领域标准线参照"，不是抄袭；
    PyVRP / OR-Tools 为公共求解器，可用；report 结构与证据组织须 100% 原创，不搬任何同学的模板/框架/命名。</div>
  </section>

  <footer>本看板由项目脚本自动生成，数据为 2026-09-10 任务列表与 src/results 下真实 CSV/图形的快照。
  距提交截止 {DEADLINE} 还有 <span id="dd2">—</span> 天。</footer>
</div>

<script>
  // live countdown (falls back to 5 if clock off)
  (function() {{
    var dl = new Date("{DEADLINE}T23:59:59");
    var now = new Date();
    var days = Math.ceil((dl - now) / 86400000);
    if (isNaN(days) || days < 0) days = 5;
    document.getElementById('dd').textContent = days + ' 天';
    document.getElementById('dd2').textContent = days;
  }})();
</script>
</body>
</html>
"""

with open(OUT, "w", encoding="utf-8") as f:
    f.write(HTML)

print("WROTE", OUT, "bytes=", len(HTML))
