import os
import re
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

# ---------- Config ----------
DEFAULT_PORT = int(os.getenv("PORT", "8000"))
AUTO_REFRESH_SECONDS = 10  # client pull interval for "real-time"
SEVERITY_PALETTE = {
    "Critical": "#DC2626",  # red-600
    "High": "#F59E0B",      # amber-500
    "Medium": "#10B981",    # emerald-500 (accessible green)
    "Low": "#3B82F6",       # blue-500
}

# ---------- Parsing Utilities ----------
EXCEPTION_BLOCK_RE = re.compile(
    r"^###\s*Exception\s*(\d+):\s*(?P<type>[^\n]+?)\s*?\n+"
    r"(?:\*\*Message\*\*:\s*(?P<message>.*?)\n)?"
    r"(?:\*\*Timestamp\*\*:\s*(?P<timestamp>.*?)\n)?"
    r"(?:\*\*Location\*\*:\s*(?P<location>.*?)\n)?"
    r"(?:\*\*Stack Trace\*\*.*?```(?P<stack>.*?)```)?",
    re.DOTALL | re.MULTILINE,
)

SUMMARY_RE = re.compile(
    r"##\s*Summary.*?"
    r"\-\s*\*\*Log File\*\*:\s*(?P<log>.*?)\n"
    r"\-\s*\*\*Total Exceptions Found\*\*:\s*(?P<total>\d+)\n"
    r"\-\s*\*\*Code Fixes Generated\*\*:\s*(?P<fixes>\d+)",
    re.DOTALL | re.IGNORECASE,
)

def infer_severity(exc_type: str, message: str) -> str:
    t = exc_type.lower()
    m = (message or "").lower()
    # Heuristics (tweak as you like):
    if "dataaccessresourcefailure" in t or "sql" in t and ("connection refused" in m or "timeout" in m):
        return "Critical"
    if "ioexception" in t and ("no space" in m or "disk" in m):
        return "Critical"
    if "nullpointer" in t:
        return "High"
    if "illegalargument" in t:
        return "Medium"
    # default
    return "Low"

def parse_timestamp(raw: Optional[str]) -> Optional[float]:
    if not raw:
        return None
    raw = raw.strip()
    # Try some common formats
    fmts = [
        "%Y-%m-%d %H:%M:%S,%f",
        "%Y-%m-%d %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ]
    for f in fmts:
        try:
            return datetime.strptime(raw, f).timestamp()
        except Exception:
            pass
    return None

def parse_report(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # Summary
    total_excs_declared = None
    fixes_declared = None
    m = SUMMARY_RE.search(text)
    log_file, total, fixes = None, None, None
    if m:
        log_file = m.group("log").strip()
        total = int(m.group("total"))
        fixes = int(m.group("fixes"))
        total_excs_declared = total
        fixes_declared = fixes

    # Exceptions
    exceptions: List[Dict[str, Any]] = []
    for m in EXCEPTION_BLOCK_RE.finditer(text):
        idx = int(m.group(1))
        etype = m.group("type").strip()
        msg = (m.group("message") or "").strip()
        ts_raw = (m.group("timestamp") or "").strip()
        loc = (m.group("location") or "").strip()
        stack = (m.group("stack") or "").strip()
        ts = parse_timestamp(ts_raw)

        severity = infer_severity(etype, msg)
        exceptions.append({
            "index": idx,
            "type": etype,
            "message": msg,
            "timestamp": ts,
            "timestamp_raw": ts_raw,
            "location": loc,
            "stack": stack,
            "severity": severity,
        })

    # Sort by timestamp if available, else by index
    exceptions.sort(key=lambda e: (e["timestamp"] is None, e["timestamp"] or e["index"]))

    # Metrics
    total_exceptions = len(exceptions)
    fixes_count = fixes_declared if fixes_declared is not None else _infer_fix_count(text)
    by_type: Dict[str, int] = {}
    by_severity: Dict[str, int] = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for e in exceptions:
        by_type[e["type"]] = by_type.get(e["type"], 0) + 1
        by_severity[e["severity"]] = by_severity.get(e["severity"], 0) + 1

    # Timeline: bucket by order (fallback) or timestamp minute
    timeline_labels: List[str] = []
    timeline_values: List[int] = []
    if any(e["timestamp"] for e in exceptions):
        # Group by minute
        buckets: Dict[str, int] = {}
        for e in exceptions:
            t = e["timestamp"]
            if t is None:
                continue
            dt = datetime.fromtimestamp(t)
            key = dt.strftime("%Y-%m-%d %H:%M")
            buckets[key] = buckets.get(key, 0) + 1
        for k in sorted(buckets.keys()):
            timeline_labels.append(k)
            timeline_values.append(buckets[k])
    else:
        # Fallback to sequential order
        for i, _ in enumerate(exceptions, 1):
            timeline_labels.append(f"Event {i}")
            timeline_values.append(1)

    # Heatmap (service health): rows = severity, cols = timeline buckets (compress to 10)
    heat_cols = min(10, max(1, len(timeline_labels)))
    # map exceptions into segments
    segment = lambda i: min(heat_cols - 1, int((i / max(1, len(exceptions))) * heat_cols))
    heatmap: Dict[str, List[int]] = {k: [0]*heat_cols for k in ["Critical","High","Medium","Low"]}
    for i, e in enumerate(exceptions):
        c = segment(i)
        heatmap[e["severity"]][c] += 1

    return {
        "source_file": path,
        "declared_log_file": log_file,
        "total_exceptions": total_exceptions,
        "code_fixes_generated": fixes_count,
        "by_type": by_type,
        "by_severity": by_severity,
        "timeline": {"labels": timeline_labels, "values": timeline_values},
        "heatmap": {"cols": heat_cols, "data": heatmap},
        "exceptions": exceptions,
        "ref_declared_total": total_excs_declared,
        "generated_at": int(time.time()),
    }

def _infer_fix_count(text: str) -> int:
    # Try to read "## Code Fix Recommendations" and count "### Fix"
    fix_matches = re.findall(r"^###\s*Fix\s*\d+:", text, re.MULTILINE)
    return len(fix_matches) if fix_matches else 0

# ---------- API ----------
@app.get("/api/data")
def api_data() -> Response:
    path = request.args.get("file", "").strip()
    if not path:
        return jsonify({"error": "Missing 'file' query param"}), 400
    try:
        data = parse_report(path)
        return jsonify(data)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to parse: {e}"}), 500

# ---------- UI ----------
INDEX_HTML = f"""<!doctype html>
<html lang="en" class="h-full">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Log Exceptions Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1"></script>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    /* Focus styles for accessibility */
    :focus {{ outline: 3px solid #3B82F6; outline-offset: 2px; }}
  </style>
</head>
<body class="min-h-screen bg-slate-50 text-slate-900">
  <div class="max-w-7xl mx-auto px-4 py-6">
    <header class="mb-6">
      <h1 class="text-2xl md:text-3xl font-bold">Exception Monitoring Dashboard</h1>
      <p class="text-slate-600">Real-time exception monitoring with interactive insights.</p>
    </header>

    <!-- Controls -->
    <section class="mb-6 flex flex-col md:flex-row gap-3 md:items-center">
      <form class="flex flex-1 gap-2" onsubmit="event.preventDefault(); updateFileParam();">
        <input id="filePath" class="flex-1 rounded-xl border p-3 shadow-sm" type="text" placeholder="Path to analysis report (e.g., /mnt/data/analysis_report_sample_spring_boot.log.md)" aria-label="Report file path" />
        <button class="rounded-2xl px-4 py-2 bg-blue-600 text-white shadow hover:bg-blue-700">Load</button>
      </form>
      <div class="text-xs text-slate-500">Auto-refresh: every {AUTO_REFRESH_SECONDS}s</div>
    </section>

    <!-- Hero cards -->
    <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <div class="bg-white rounded-2xl p-4 shadow">
        <div class="text-sm text-slate-500">Total Exceptions</div>
        <div id="metricTotal" class="text-3xl font-bold">—</div>
      </div>
      <div class="bg-white rounded-2xl p-4 shadow">
        <div class="text-sm text-slate-500">Code Fixes Generated</div>
        <div id="metricFixes" class="text-3xl font-bold">—</div>
      </div>
      <div class="bg-white rounded-2xl p-4 shadow">
        <div class="text-sm text-slate-500">Most Common Type</div>
        <div id="metricCommon" class="text-3xl font-bold">—</div>
      </div>
      <div class="bg-white rounded-2xl p-4 shadow">
        <div class="text-sm text-slate-500">Last Updated</div>
        <div id="metricUpdated" class="text-3xl font-bold">—</div>
      </div>
    </section>

    <!-- Charts grid -->
    <section class="grid grid-cols-1 lg:grid-cols-5 gap-6">
      <div class="lg:col-span-3 bg-white rounded-2xl p-4 shadow">
        <h2 class="font-semibold mb-2">Exception Types (Bar)</h2>
        <canvas id="typesBar" role="img" aria-label="Bar chart of exception types"></canvas>
      </div>
      <div class="lg:col-span-2 bg-white rounded-2xl p-4 shadow">
        <h2 class="font-semibold mb-2">Severity Distribution</h2>
        <canvas id="severityPie" role="img" aria-label="Pie chart of severity distribution"></canvas>
      </div>
      <div class="lg:col-span-3 bg-white rounded-2xl p-4 shadow">
        <h2 class="font-semibold mb-2">Timeline (Line)</h2>
        <canvas id="timelineLine" role="img" aria-label="Line chart of exceptions over time"></canvas>
      </div>
      <div class="lg:col-span-2 bg-white rounded-2xl p-4 shadow">
        <h2 class="font-semibold mb-2">Service Health (Heatmap)</h2>
        <canvas id="heatmap" role="img" aria-label="Heatmap of service health"></canvas>
      </div>
    </section>

    <!-- Details (progressive disclosure) -->
    <section class="mt-6 bg-white rounded-2xl p-4 shadow">
      <h2 class="font-semibold mb-3">Exceptions (Details)</h2>
      <div id="exceptionList" class="space-y-2"></div>
    </section>

    <!-- Footer -->
    <footer class="mt-8 text-xs text-slate-500">Accessible color keys: 
      <span class="inline-flex items-center gap-1"><span class="inline-block w-3 h-3 rounded-sm bg-red-600"></span>Critical</span>,
      <span class="inline-flex items-center gap-1"><span class="inline-block w-3 h-3 rounded-sm bg-amber-500"></span>High</span>,
      <span class="inline-flex items-center gap-1"><span class="inline-block w-3 h-3 rounded-sm bg-emerald-500"></span>Medium</span>,
      <span class="inline-flex items-center gap-1"><span class="inline-block w-3 h-3 rounded-sm bg-blue-500"></span>Low</span>
    </footer>
  </div>

<script>
const SEVERITY_COLORS = {{
  "Critical": "{SEVERITY_PALETTE['Critical']}",
  "High": "{SEVERITY_PALETTE['High']}",
  "Medium": "{SEVERITY_PALETTE['Medium']}",
  "Low": "{SEVERITY_PALETTE['Low']}",
}};

let charts = {{ typesBar: null, severityPie: null, timelineLine: null, heatmap: null }};
let currentFile = null;

function getParam(name) {{
  return new URLSearchParams(window.location.search).get(name);
}}

function updateFileParam() {{
  const p = document.getElementById('filePath').value.trim();
  if (!p) return;
  const url = new URL(window.location);
  url.searchParams.set('file', p);
  window.history.replaceState(null, '', url);
  currentFile = p;
  fetchAndRender();
}}

function sumVals(obj) {{
  return Object.values(obj).reduce((a,b)=>a+b,0);
}}

function fmtTime(ts) {{
  const d = new Date(ts*1000);
  return d.toLocaleString();
}}

async function fetchData() {{
  const file = getParam('file');
  if (!file) return {{error: "No file parameter"}};
  const res = await fetch(`/api/data?file=${{encodeURIComponent(file)}}`);
  return res.json();
}}

function ensureChart(ctxId, cfg) {{
  if (charts[ctxId]) charts[ctxId].destroy();
  const ctx = document.getElementById(ctxId);
  charts[ctxId] = new Chart(ctx, cfg);
}}

function render(data) {{
  // Hero metrics
  document.getElementById('metricTotal').textContent = data.total_exceptions ?? '—';
  document.getElementById('metricFixes').textContent = data.code_fixes_generated ?? '—';
  const commonType = Object.entries(data.by_type || {{}}).sort((a,b)=>b[1]-a[1])[0];
  document.getElementById('metricCommon').textContent = commonType ? `${{commonType[0]}} (${{commonType[1]}})` : '—';
  document.getElementById('metricUpdated').textContent = data.generated_at ? fmtTime(data.generated_at) : '—';

  // Types bar
  const typeLabels = Object.keys(data.by_type || {{}}); 
  const typeValues = typeLabels.map(k => data.by_type[k]);
  ensureChart('typesBar', {{
    type: 'bar',
    data: {{
      labels: typeLabels,
      datasets: [{{
        label: 'Count',
        data: typeValues
      }}]
    }},
    options: {{
      responsive: true,
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{ mode: 'index', intersect: false }}
      }},
      scales: {{ x: {{ ticks: {{ autoSkip: false }} }}, y: {{ beginAtZero: true }} }}
    }}
  }});

  // Severity pie
  const sevLabels = ['Critical','High','Medium','Low'];
  const sevValues = sevLabels.map(k => (data.by_severity && data.by_severity[k]) || 0);
  const sevColors = sevLabels.map(k => SEVERITY_COLORS[k]);
  ensureChart('severityPie', {{
    type: 'pie',
    data: {{
      labels: sevLabels,
      datasets: [{{
        data: sevValues,
        backgroundColor: sevColors
      }}]
    }},
    options: {{
      responsive: true,
      plugins: {{ legend: {{ position: 'bottom' }} }}
    }}
  }});

  // Timeline line
  ensureChart('timelineLine', {{
    type: 'line',
    data: {{
      labels: data.timeline?.labels || [],
      datasets: [{{
        label: 'Exceptions',
        data: data.timeline?.values || [],
        fill: false,
        tension: 0.2
      }}]
    }},
    options: {{
      responsive: true,
      plugins: {{
        legend: {{ display: false }}
      }},
      scales: {{ y: {{ beginAtZero: true, precision: 0 }} }}
    }}
  }});

  // Heatmap (simple squares via bar stack)
  // Flatten severity rows across columns using stacked bars per column
  const cols = data.heatmap?.cols || 1;
  const hmData = data.heatmap?.data || {{}};
  const colLabels = Array.from({{length: cols}}, (_,i)=>`T${{i+1}}`);
  const ds = Object.keys(SEVERITY_COLORS).map(sev => ({{
    label: sev, stack: 'S',
    data: (hmData[sev] || Array(cols).fill(0)),
    backgroundColor: SEVERITY_COLORS[sev]
  }}));
  ensureChart('heatmap', {{
    type: 'bar',
    data: {{ labels: colLabels, datasets: ds }},
    options: {{
      responsive: true,
      plugins: {{
        legend: {{ position: 'bottom' }},
        tooltip: {{ mode: 'index', intersect: false }}
      }},
      scales: {{
        x: {{ stacked: true }},
        y: {{ stacked: true, beginAtZero: true, ticks: {{ precision: 0 }} }}
      }}
    }}
  }});

  // Details list (progressive disclosure)
  const list = document.getElementById('exceptionList');
  list.innerHTML = '';
  (data.exceptions || []).forEach(e => {{
    const wrapper = document.createElement('details');
    wrapper.className = 'rounded-xl border p-3';
    const sevColor = SEVERITY_COLORS[e.severity] || '#64748B';
    wrapper.innerHTML = `
      <summary class="cursor-pointer flex flex-wrap items-center gap-2">
        <span class="font-semibold">${{e.type}}</span>
        <span class="text-xs px-2 py-0.5 rounded-full" style="background:${{sevColor}}20;color:${{sevColor}};border:1px solid ${{sevColor}}40">${{e.severity}}</span>
        <span class="text-slate-500 text-sm">#${{e.index}}</span>
        <span class="text-slate-400 text-xs ml-auto">${{e.timestamp_raw || 'No timestamp'}}</span>
      </summary>
      <div class="mt-2 grid gap-2 text-sm">
        <div><span class="text-slate-500">Message:</span> ${{e.message || '—'}}</div>
        <div><span class="text-slate-500">Location:</span> ${{e.location || '—'}}</div>
        ${{e.stack ? `<pre class="bg-slate-50 rounded p-2 overflow-x-auto text-[11px]">${{e.stack.replace(/[<>&]/g, s => ({{'<':'&lt;','>':'&gt;','&':'&amp;'}})[s]))}}</pre>` : ''}}
      </div>
    `;
    list.appendChild(wrapper);
  }});
}}

async function fetchAndRender() {{
  const data = await fetchData();
  if (data.error) {{
    alert(data.error);
    return;
  }}
  render(data);
}}

function init() {{
  const file = getParam('file');
  if (file) document.getElementById('filePath').value = file;
  if (file) fetchAndRender();
  setInterval(() => {{
    if (getParam('file')) fetchAndRender();
  }}, {AUTO_REFRESH_SECONDS * 1000});
}}

window.addEventListener('DOMContentLoaded', init);
</script>
</body>
</html>
"""

@app.get("/")
def index():
    return Response(INDEX_HTML, mimetype="text/html")

# ---------- Entry ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=DEFAULT_PORT, debug=False)
