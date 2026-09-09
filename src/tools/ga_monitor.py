"""
Live progress monitor for baseline_ga_vrptw.py multi-seed run.

Reads the tail of the running GA log, parses how many Solomon instances have
finished (out of 56), the running per-family / overall mean gap, and serves a
small auto-refreshing HTML dashboard at http://localhost:8770 .

Run:
    python src/tools/ga_monitor.py
Then open http://localhost:8770 in a browser (the page polls /api every 2s).
"""
import json
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_PATH = os.path.join(ROOT, "src", "results", "baseline_ga_multi_seed.log")
PORT = 8770
TOTAL = 56          # 56 Solomon instances
SEEDS = 5           # seeds per instance
SEC_PER_INST = 40   # 5 seeds x ~8s, rough ETA basis

START_TIME = time.time()

FAMILIES = ("C1", "C2", "R1", "R2", "RC1", "RC2")


def _fam(name):
    if name.startswith("RC"):
        return "RC1" if name[2] == "1" else "RC2"
    head = name[0]
    return f"{head}{name[1]}"


def parse_log():
    done, gaps, fam_gaps = [], [], {f: [] for f in FAMILIES}
    finished = False
    overall = None
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, encoding="utf-8", errors="ignore") as fh:
            for raw in fh:
                line = raw.rstrip("\n")
                s = line.strip()
                if s.startswith("OVERALL"):
                    finished = True
                    overall = s
                    continue
                parts = s.split()
                if len(parts) >= 9 and parts[-1] in ("OK", "FAIL"):
                    name = parts[0]
                    if not (name[0] in "CR"):
                        continue
                    rec = {"inst": name, "status": parts[-1]}
                    if parts[-1] == "OK":
                        try:
                            gap = float(parts[5])
                            rec["gap"] = gap
                            gaps.append(gap)
                            fam_gaps[_fam(name)].append(gap)
                        except (ValueError, IndexError):
                            pass
                    done.append(rec)

    n = len(done)
    elapsed = time.time() - START_TIME
    remaining = max(TOTAL - n, 0)
    # ETA: prefer observed rate once >=2 instances done, else static estimate
    if n >= 2 and elapsed > 0:
        rate = elapsed / n
        eta = remaining * rate
    else:
        eta = remaining * SEC_PER_INST

    return {
        "total": TOTAL,
        "seeds": SEEDS,
        "done": n,
        "finished": finished,
        "overall": overall,
        "pct": round(100.0 * n / TOTAL, 1),
        "mean_gap": round(sum(gaps) / len(gaps), 2) if gaps else None,
        "fam_gap": {
            f: (round(sum(v) / len(v), 1) if v else None, len(v))
            for f, v in fam_gaps.items()
        },
        "recent": done[-12:][::-1],
        "elapsed": int(elapsed),
        "eta": int(eta),
    }


PAGE = """<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GA 多种子基线 · 实时进度</title>
<style>
  :root{ --bg:#0f1115; --panel:#171a21; --line:#262b36; --txt:#e6e9ef;
         --dim:#9aa4b2; --accent:#4c8dff; --ok:#3fbf7f; --warn:#e6a23c; }
  *{ box-sizing:border-box; }
  body{ margin:0; font-family:"Segoe UI",system-ui,sans-serif; background:var(--bg);
        color:var(--txt); padding:28px; }
  .wrap{ max-width:860px; margin:0 auto; }
  h1{ font-size:20px; font-weight:600; margin:0 0 4px; }
  .sub{ color:var(--dim); font-size:13px; margin-bottom:22px; }
  .card{ background:var(--panel); border:1px solid var(--line); border-radius:12px;
         padding:20px 22px; margin-bottom:16px; }
  .bigrow{ display:flex; align-items:baseline; gap:14px; margin-bottom:14px; }
  .big{ font-size:40px; font-weight:700; letter-spacing:-1px; }
  .big small{ font-size:18px; color:var(--dim); font-weight:400; }
  .bar{ height:16px; background:#0b0d11; border-radius:8px; overflow:hidden;
        border:1px solid var(--line); }
  .fill{ height:100%; background:linear-gradient(90deg,#4c8dff,#7db1ff);
         width:0%; transition:width .5s ease; }
  .fill.done{ background:linear-gradient(90deg,#3fbf7f,#63d69a); }
  .stats{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-top:16px; }
  .stat{ background:#0b0d11; border:1px solid var(--line); border-radius:9px; padding:12px 14px; }
  .stat .k{ color:var(--dim); font-size:12px; margin-bottom:4px; }
  .stat .v{ font-size:20px; font-weight:600; }
  h2{ font-size:14px; color:var(--dim); font-weight:600; margin:0 0 12px;
      text-transform:uppercase; letter-spacing:.5px; }
  table{ width:100%; border-collapse:collapse; font-size:13px; }
  th,td{ text-align:left; padding:7px 10px; border-bottom:1px solid var(--line); }
  th{ color:var(--dim); font-weight:500; }
  td.num{ text-align:right; font-variant-numeric:tabular-nums; }
  .fam{ display:flex; gap:10px; flex-wrap:wrap; }
  .chip{ background:#0b0d11; border:1px solid var(--line); border-radius:20px;
         padding:6px 14px; font-size:13px; }
  .chip b{ color:var(--accent); }
  .pill{ display:inline-block; padding:2px 9px; border-radius:12px; font-size:12px; }
  .pill.ok{ background:rgba(63,191,127,.15); color:var(--ok); }
  .pill.fail{ background:rgba(230,71,71,.15); color:#f16b6b; }
  .live{ display:inline-block; width:8px; height:8px; border-radius:50%;
         background:var(--ok); margin-right:6px; animation:pulse 1.4s infinite; }
  @keyframes pulse{ 0%,100%{opacity:1;} 50%{opacity:.25;} }
  .muted{ color:var(--dim); font-size:12px; }
</style></head>
<body><div class="wrap">
  <h1>GA 多种子基线 · 实时进度</h1>
  <div class="sub"><span class="live"></span><span id="livetxt">监控中</span>
     · Solomon VRPTW 56 实例 × 5 种子 · 每 2 秒自动刷新</div>

  <div class="card">
    <div class="bigrow">
      <div class="big"><span id="done">0</span><small>/ 56 实例</small></div>
      <div class="big" style="margin-left:auto;font-size:30px;color:var(--accent)">
        <span id="pct">0</span><small>%</small></div>
    </div>
    <div class="bar"><div class="fill" id="fill"></div></div>
    <div class="stats">
      <div class="stat"><div class="k">当前平均 gap</div><div class="v" id="gap">—</div></div>
      <div class="stat"><div class="k">已用时</div><div class="v" id="elapsed">—</div></div>
      <div class="stat"><div class="k">预计剩余</div><div class="v" id="eta">—</div></div>
      <div class="stat"><div class="k">状态</div><div class="v" id="state">运行中</div></div>
    </div>
  </div>

  <div class="card">
    <h2>各家族平均 gap（已完成实例）</h2>
    <div class="fam" id="fam"></div>
  </div>

  <div class="card">
    <h2>最近完成的实例</h2>
    <table><thead><tr><th>实例</th><th>状态</th><th class="num">gap %</th></tr></thead>
    <tbody id="rows"></tbody></table>
    <div class="muted" id="overall" style="margin-top:12px"></div>
  </div>
</div>

<script>
function fmt(s){ if(s==null) return "—";
  const m=Math.floor(s/60), sec=s%60; return m+"m "+sec+"s"; }
async function tick(){
  try{
    const r = await fetch("/api",{cache:"no-store"});
    const d = await r.json();
    document.getElementById("done").textContent = d.done;
    document.getElementById("pct").textContent = d.pct;
    const fill = document.getElementById("fill");
    fill.style.width = d.pct + "%";
    document.getElementById("gap").textContent =
        d.mean_gap==null ? "—" : d.mean_gap + "%";
    document.getElementById("elapsed").textContent = fmt(d.elapsed);
    document.getElementById("eta").textContent = d.finished ? "—" : fmt(d.eta);
    document.getElementById("state").textContent = d.finished ? "已完成 ✅" : "运行中";
    if(d.finished){ fill.classList.add("done");
       document.getElementById("livetxt").textContent="已完成"; }
    // families
    const fam = document.getElementById("fam"); fam.innerHTML="";
    for(const k in d.fam_gap){
      const [g,n] = d.fam_gap[k];
      const c = document.createElement("div"); c.className="chip";
      c.innerHTML = k+" · <b>"+(g==null?"—":g+"%")+"</b> <span class='muted'>("+n+")</span>";
      fam.appendChild(c);
    }
    // recent rows
    const tb = document.getElementById("rows"); tb.innerHTML="";
    for(const x of d.recent){
      const tr=document.createElement("tr");
      const pill = x.status==="OK" ? "<span class='pill ok'>OK</span>"
                                   : "<span class='pill fail'>FAIL</span>";
      tr.innerHTML = "<td>"+x.inst+"</td><td>"+pill+"</td><td class='num'>"+
                     (x.gap==null?"—":x.gap.toFixed(1))+"</td>";
      tb.appendChild(tr);
    }
    document.getElementById("overall").textContent = d.overall || "";
  }catch(e){ document.getElementById("livetxt").textContent="等待日志..."; }
}
tick(); setInterval(tick, 2000);
</script>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silence console
        pass

    def do_GET(self):
        if self.path.startswith("/api"):
            body = json.dumps(parse_log()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        else:
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)


if __name__ == "__main__":
    print(f"GA monitor on http://localhost:{PORT}  (log: {LOG_PATH})")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
