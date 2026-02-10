import os
import re
from pathlib import Path
from datetime import datetime
import csv
import json

ROOT = Path(r"/opt/Zenatus_Backtester")
OUT_DIR = ROOT / "10_Tree"
DAILY_DIR = OUT_DIR / "Projectstructure" / "Daily"
PATHS_DIR = OUT_DIR / "Paths"
DAILY_DIR.mkdir(parents=True, exist_ok=True)
PATHS_DIR.mkdir(parents=True, exist_ok=True)

def now_date_str():
    dt = datetime.now()
    return dt.strftime("%d_%m_%Y")

def ext_of(p: Path):
    return p.suffix.lower()

def list_all(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dp = Path(dirpath)
        yield dp, [dp / f for f in filenames], [dp / d for d in dirnames]

def tree_markdown(root: Path):
    lines = []
    prefix_len = len(str(root))
    for dp, files, dirs in list_all(root):
        rel = str(dp)[prefix_len:].lstrip("\\/")
        depth = 0 if rel == "" else rel.count("\\") + rel.count("/")
        name = root.name if rel == "" else dp.name
        lines.append(f"{'  ' * depth}- {name}/")
        for f in sorted(files):
            lines.append(f"{'  ' * (depth + 1)}- {f.name}")
    return "\n".join(lines)

def collect_counts(root: Path):
    counts = {}
    folders = 0
    for dp, files, dirs in list_all(root):
        folders += 1
        for f in files:
            ext = ext_of(f) or ""
            counts[ext] = counts.get(ext, 0) + 1
    return folders, counts

def color_for_ext(ext: str):
    m = {
        ".py": "#1f77b4",
        ".csv": "#f2c811",
        ".md": "#2ca02c",
        ".json": "#ff7f0e",
        ".txt": "#7f7f7f",
        ".xml": "#8c564b",
        ".yml": "#17becf",
        ".yaml": "#17becf",
        ".png": "#e377c2",
        ".jpg": "#e377c2",
        ".jpeg": "#e377c2",
        "": "#444444"
    }
    return m.get(ext, "#9467bd")

def render_metrics_html(date_str: str, folders: int, counts: dict, ext_list: list, history: dict, base_dir: str):
    total_files = sum(counts.values())
    rows = []
    for ext in sorted(ext_list):
        c = counts.get(ext, 0)
        color = color_for_ext(ext)
        label = ext if ext else "(no ext)"
        rows.append("<tr data-ext='" + label + "' data-count='" + str(c) + "'><td class='col-ext'>" + label + "</td><td class='col-count' style='text-align:right'>" + str(c) + "</td><td><div class='bar-bg'><div class='bar' style='width:" + f"{(c/max(total_files,1))*100:.2f}" + "%;background:" + color + "'></div></div></td></tr>")
    prev_day = history.get("prev_day")
    prev_week = history.get("prev_week")
    prev_month = history.get("prev_month")
    def delta(a, b):
        if a is None or b is None:
            return None, None
        diff = a - b
        pct = (diff / b * 100) if b else 0.0
        return diff, pct
    d_files, d_files_pct = delta(total_files, prev_day["total_files"] if prev_day else None)
    d_folders, d_folders_pct = delta(folders, prev_day["folders"] if prev_day else None)
    w_files, w_files_pct = delta(total_files, prev_week["total_files"] if prev_week else None)
    m_files, m_files_pct = delta(total_files, prev_month["total_files"] if prev_month else None)
    prev_date = history.get("prev_date")
    next_date = history.get("next_date")
    html = []
    html.append("<!doctype html><html><head><meta charset=\"utf-8\"><title>File Metrics " + date_str + "</title>")
    html.append("<style>")
    html.append("body{font-family:system-ui,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:0;background:#f6f8fa;color:#222}")
    html.append(".container{max-width:1100px;margin:40px auto;padding:0 20px}")
    html.append(".cards{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px}")
    html.append(".card{background:#fff;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.08);padding:16px}")
    html.append("h1{margin:0 0 12px 0;font-size:22px;display:flex;align-items:center;gap:10px}")
    html.append(".nav-btn{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:6px;border:1px solid #ddd;cursor:pointer;color:#fff}")
    html.append(".nav-btn.prev{background:#e53935;border-color:#e53935}")
    html.append(".nav-btn.next{background:#43a047;border-color:#43a047}")
    html.append(".nav-btn:disabled{opacity:.4;cursor:not-allowed}")
    html.append(".controls{display:flex;gap:8px;margin-bottom:12px}")
    html.append(".filter{flex:1}")
    html.append(".sort-btn{padding:6px 10px;border:1px solid #ddd;border-radius:6px;background:#fff;cursor:pointer}")
    html.append("table{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.08)}")
    html.append("th,td{padding:10px 12px;border-bottom:1px solid #eee}")
    html.append("th{text-align:left;background:#fafafa}")
    html.append(".grid{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}")
    html.append(".badge{color:#fff;padding:6px 10px;border-radius:8px;font-size:12px}")
    html.append(".muted{color:#666}")
    html.append(".bar-bg{height:10px;background:#eee;border-radius:6px}")
    html.append(".bar{height:10px;border-radius:6px}")
    html.append(".delta-pos{color:#0a8f2e}")
    html.append(".delta-neg{color:#c81e1e}")
    html.append(".delta-zero{color:#666}")
    html.append("</style></head><body>")
    html.append("<div class=\"container\">")
    html.append("<h1>")
    html.append("<button class=\"nav-btn prev\" id=\"btnPrev\" title=\"Vortag\" " + ("" if prev_date else "disabled") + ">&larr;</button>")
    html.append("<div>Projekt-Metriken " + date_str + "</div>")
    html.append("<button class=\"nav-btn next\" id=\"btnNext\" title=\"Nächster Tag\" " + ("" if next_date else "disabled") + ">&rarr;</button>")
    html.append("</h1>")
    html.append("<div class=\"cards\">")
    html.append("<div class=\"card\"><div class=\"muted\">Ordner</div><div style=\"font-size:20px;font-weight:600\">" + str(folders) + "</div></div>")
    html.append("<div class=\"card\"><div class=\"muted\">Dateien gesamt</div><div style=\"font-size:20px;font-weight:600\">" + str(total_files) + "</div></div>")
    html.append("<div class=\"card\"><div class=\"muted\">Dateitypen</div><div style=\"font-size:20px;font-weight:600\">" + str(len(ext_list)) + "</div></div>")
    html.append("</div>")
    html.append("<div class=\"cards\" style=\"grid-template-columns:repeat(3,1fr)\">")
    html.append("<div class=\"card\"><div class=\"muted\">Vortag</div>")
    html.append("<div style=\"font-size:16px;font-weight:600\">" + (prev_day["date"] if prev_day else "—") + "</div>")
    html.append("<div>Dateien: <span class=\"" + ("delta-pos" if (d_files or 0)>0 else ("delta-neg" if (d_files or 0)<0 else "delta-zero")) + "\">" + ((f"{d_files:+} ({d_files_pct:+.2f}%)") if d_files is not None else "—") + "</span></div>")
    html.append("<div>Ordner: <span class=\"" + ("delta-pos" if (d_folders or 0)>0 else ("delta-neg" if (d_folders or 0)<0 else "delta-zero")) + "\">" + ((f"{d_folders:+}") if d_folders is not None else "—") + "</span></div>")
    html.append("</div>")
    html.append("<div class=\"card\"><div class=\"muted\">Woche davor</div>")
    html.append("<div style=\"font-size:16px;font-weight:600\">" + (prev_week["date"] if prev_week else "—") + "</div>")
    html.append("<div>Dateien: <span class=\"" + ("delta-pos" if (w_files or 0)>0 else ("delta-neg" if (w_files or 0)<0 else "delta-zero")) + "\">" + ((f"{w_files:+} ({w_files_pct:+.2f}%)") if w_files is not None else "—") + "</span></div>")
    html.append("</div>")
    html.append("<div class=\"card\"><div class=\"muted\">Monat davor</div>")
    html.append("<div style=\"font-size:16px;font-weight:600\">" + (prev_month["date"] if prev_month else "—") + "</div>")
    html.append("<div>Dateien: <span class=\"" + ("delta-pos" if (m_files or 0)>0 else ("delta-neg" if (m_files or 0)<0 else "delta-zero")) + "\">" + ((f"{m_files:+} ({m_files_pct:+.2f}%)") if m_files is not None else "—") + "</span></div>")
    html.append("</div>")
    html.append("</div>")
    html.append("<div class=\"controls\">")
    html.append("<input id=\"filterInput\" class=\"filter\" type=\"text\" placeholder=\"Filter nach Datentyp…\">")
    html.append("<button id=\"sortExt\" class=\"sort-btn\">Sortiere nach Name</button>")
    html.append("<button id=\"sortCount\" class=\"sort-btn\">Sortiere nach Anzahl</button>")
    html.append("<input id=\"datePicker\" type=\"date\" class=\"sort-btn\" title=\"Zu Datum springen\">")
    html.append("</div>")
    html.append("<table>")
    html.append("<thead><tr><th>Dateityp</th><th style=\"text-align:right\">Anzahl</th><th>Verteilung</th></tr></thead>")
    html.append("<tbody>")
    html.append("".join(rows))
    html.append("</tbody>")
    html.append("</table>")
    html.append("<div class=\"grid\">")
    html.append("".join([f"<span class='badge' style='background:{color_for_ext(ext)}'>{ext if ext else '(no ext)'}: {counts.get(ext,0)}</span>" for ext in sorted(ext_list)]))
    html.append("</div>")
    html.append("</div>")
    html.append("<script type=\"application/json\" id=\"metrics-json\">" + json.dumps({"date": date_str, "folders": folders, "total_files": total_files, "extensions": counts}, ensure_ascii=False) + "</script>")
    html.append("<script type=\"application/json\" id=\"history-json\">" + json.dumps(history, ensure_ascii=False) + "</script>")
    html.append("<script>")
    html.append("const baseDir = " + json.dumps(base_dir) + ";")
    html.append("const metrics = JSON.parse(document.getElementById('metrics-json').textContent);")
    html.append("const history = JSON.parse(document.getElementById('history-json').textContent);")
    html.append("const tbody = document.querySelector('tbody');")
    html.append("const filterInput = document.getElementById('filterInput');")
    html.append("const sortExtBtn = document.getElementById('sortExt');")
    html.append("const sortCountBtn = document.getElementById('sortCount');")
    html.append("const btnPrev = document.getElementById('btnPrev');")
    html.append("const btnNext = document.getElementById('btnNext');")
    html.append("const datePicker = document.getElementById('datePicker');")
    html.append("function navigateTo(dateStr){ if(!dateStr) return; const target = baseDir + '/' + dateStr + '_filemetrics.html'; window.location.href = target; }")
    html.append("if(btnPrev) btnPrev.onclick = ()=> navigateTo(history.prev_date);")
    html.append("if(btnNext) btnNext.onclick = ()=> navigateTo(history.next_date);")
    html.append("document.addEventListener('keydown', (e)=>{ if(e.key === 'ArrowLeft' && history.prev_date){ navigateTo(history.prev_date); } if(e.key === 'ArrowRight' && history.next_date){ navigateTo(history.next_date); } });")
    html.append("if(history.all_dates && history.all_dates.length){ const parts = metrics.date.split('_'); const iso = parts[2] + '-' + parts[1] + '-' + parts[0]; datePicker.value = iso; datePicker.addEventListener('change', ()=>{ const d = datePicker.value.split('-'); const target = d[2] + '_' + d[1] + '_' + d[0]; if(history.all_dates.includes(target)){ navigateTo(target); } else { alert('Kein Snapshot für dieses Datum vorhanden.'); } }); }")
    html.append("let sortNameAsc = true; let sortCountDesc = true;")
    html.append("function sortByExt(dir){ const rows = Array.from(tbody.querySelectorAll('tr')); rows.sort((a,b)=>{ const cmp=a.dataset.ext.localeCompare(b.dataset.ext); return dir==='asc'?cmp:-cmp; }); tbody.replaceChildren(...rows);} ")
    html.append("function sortByCount(dir){ const rows = Array.from(tbody.querySelectorAll('tr')); rows.sort((a,b)=>{ const da=parseInt(a.dataset.count); const db=parseInt(b.dataset.count); return dir==='desc'?(db-da):(da-db); }); tbody.replaceChildren(...rows);} ")
    html.append("sortExtBtn.onclick = ()=>{ sortByExt(sortNameAsc?'asc':'desc'); sortNameAsc=!sortNameAsc; }; ")
    html.append("sortCountBtn.onclick = ()=>{ sortByCount(sortCountDesc?'desc':'asc'); sortCountDesc=!sortCountDesc; }; ")
    html.append("filterInput.addEventListener('input', ()=>{ const q = filterInput.value.trim().toLowerCase(); Array.from(tbody.querySelectorAll('tr')).forEach(tr=>{ const ext = tr.dataset.ext.toLowerCase(); tr.style.display = ext.includes(q) ? '' : 'none'; }); });")
    html.append("</script></body></html>")
    return "".join(html)

def write_history_csv(history_csv: Path, date_str: str, folders: int, counts: dict):
    ext_keys = sorted(counts.keys())
    header = ["date", "folders", "total_files"] + ext_keys
    rows = []
    if history_csv.exists():
        with history_csv.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)
            old_header = next(reader, None)
            old_rows = [r for r in reader if r]
        current_keys = old_header[3:] if old_header and len(old_header) >= 3 else []
        all_keys = sorted(set(current_keys) | set(ext_keys))
        header = ["date", "folders", "total_files"] + all_keys
        # build map by date, keep latest
        by_date = {}
        for r in old_rows:
            by_date[r[0]] = r
        # update today's row
        today_row = [date_str, str(folders), str(sum(counts.values()))] + [str(counts.get(k, 0)) for k in all_keys]
        by_date[date_str] = today_row
        # normalize all rows to new header keys
        for d, r in by_date.items():
            row_map = {}
            for i, k in enumerate(current_keys):
                if 3 + i < len(r):
                    row_map[k] = r[3 + i]
            normalized = [d, r[1], r[2]] + [row_map.get(k, "0") for k in all_keys]
            rows.append(normalized)
        # sort by date
        rows = sorted(rows, key=lambda r: datetime.strptime(r[0], "%d_%m_%Y"))
    else:
        rows = [[date_str, str(folders), str(sum(counts.values()))] + [str(counts.get(k, 0)) for k in ext_keys]]
    history_csv.parent.mkdir(parents=True, exist_ok=True)
    with history_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)

PATH_REGEX = re.compile(r"([A-Za-z]:\\\\[^\\s\"']+|\\\\\\\\[^\\s\"']+|[A-Za-z]:/[^\\s\"']+|//[^\\s\"']+)")

def scan_paths(root: Path):
    results = []
    target_exts = {".bat", ".cmd", ".py", ".json", ".md"}
    ignore_exts = {".txt"}
    for dp, files, dirs in list_all(root):
        for f in files:
            ext = ext_of(f)
            if ext in ignore_exts:
                continue
            if ext not in target_exts:
                continue
            try:
                with f.open("r", encoding="utf-8", errors="ignore") as fh:
                    for idx, line in enumerate(fh, 1):
                        for m in PATH_REGEX.finditer(line):
                            results.append({"file": str(f), "line": idx, "path": m.group(0)})
            except:
                pass
    return results

def read_history(history_csv: Path):
    if not history_csv.exists():
        return {"rows": [], "dates": [], "header": ["date","folders","total_files"]}
    with history_csv.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        rows = [r for r in reader if r]
    # dedupe by date, keep last occurrence
    by_date = {}
    for r in rows:
        by_date[r[0]] = r
    dates = sorted(by_date.keys(), key=lambda s: datetime.strptime(s, "%d_%m_%Y"))
    return {"rows": [by_date[d] for d in dates], "dates": dates, "header": header}

def main():
    date_str = now_date_str()
    detailed_name = DAILY_DIR / f"{date_str}_projectstucture.md"
    metrics_html_name = DAILY_DIR / f"{date_str}_filemetrics.html"
    history_csv = OUT_DIR / "Projectstructure" / "filemetrics_history.csv"
    folders, counts = collect_counts(ROOT)
    ext_list = sorted(counts.keys())
    detailed = tree_markdown(ROOT)
    detailed_name.write_text(detailed, encoding="utf-8")
    # Update history
    write_history_csv(history_csv, date_str, folders, counts)
    # Build history info for HTML
    hist = read_history(history_csv)
    dates = hist.get("dates", [])
    header = hist.get("header", [])
    def row_to_obj(r):
        if not r:
            return None
        data = {"date": r[0], "folders": int(r[1]), "total_files": int(r[2])}
        # extension counts start at index 3 following header
        ext_keys = header[3:] if header and len(header) >= 3 else []
        ext_counts = {}
        for i, k in enumerate(ext_keys):
            if 3 + i < len(r):
                try:
                    ext_counts[k] = int(r[3 + i])
                except:
                    ext_counts[k] = 0
        data["extensions"] = ext_counts
        return data
    idx = dates.index(date_str) if date_str in dates else -1
    prev_date = dates[idx-1] if idx > 0 else None
    next_date = dates[idx+1] if idx >= 0 and idx < len(dates)-1 else None
    # compute prev week/month target dates (closest earlier snapshot)
    def closest_before(target_dt):
        for d in reversed(dates):
            dt = datetime.strptime(d, "%d_%m_%Y")
            if dt <= target_dt:
                return d
        return None
    cur_dt = datetime.strptime(date_str, "%d_%m_%Y")
    week_dt = cur_dt.replace()  # copy
    month_dt = cur_dt.replace()
    from datetime import timedelta
    week_dt = cur_dt - timedelta(days=7)
    month_dt = cur_dt - timedelta(days=30)
    prev_week_date = closest_before(week_dt)
    prev_month_date = closest_before(month_dt)
    prev_day_obj = row_to_obj(hist["rows"][dates.index(prev_date)]) if prev_date else None
    prev_week_obj = row_to_obj(hist["rows"][dates.index(prev_week_date)]) if prev_week_date else None
    prev_month_obj = row_to_obj(hist["rows"][dates.index(prev_month_date)]) if prev_month_date else None
    history_info = {
        "prev_date": prev_date,
        "next_date": next_date,
        "all_dates": dates,
        "prev_day": prev_day_obj,
        "prev_week": prev_week_obj,
        "prev_month": prev_month_obj
    }
    metrics_html = render_metrics_html(date_str, folders, counts, ext_list, history_info, str(metrics_html_name.parent).replace("\\", "/"))
    metrics_html_name.write_text(metrics_html, encoding="utf-8")
    # Timeline HTML
    def render_timeline_html(hist_obj):
        rows = hist_obj.get("rows", [])
        dates = hist_obj.get("dates", [])
        header = hist_obj.get("header", ["date","folders","total_files"])
        data = []
        for r in rows:
            try:
                data.append({"date": r[0], "folders": int(r[1]), "total_files": int(r[2])})
            except:
                pass
        ext_keys = header[3:] if header and len(header) >= 3 else []
        ext_series = {}
        for k in ext_keys:
            ext_series[k] = []
        for r in rows:
            for i,k in enumerate(ext_keys):
                val = 0
                if 3+i < len(r):
                    try: val = int(r[3+i])
                    except: val = 0
                ext_series[k].append(val)
        html = []
        html.append("<!doctype html><html><head><meta charset='utf-8'><title>Projekt Timeline</title><style>")
        html.append("body{font-family:system-ui,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:0;background:#f6f8fa;color:#222}")
        html.append(".container{max-width:1200px;margin:40px auto;padding:0 20px}")
        html.append("h1{margin:0 0 12px 0;font-size:22px}")
        html.append(".chart{background:#fff;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.08);padding:16px;margin-bottom:16px}")
        html.append(".scroll{overflow-x:auto;padding-bottom:10px}")
        html.append("canvas{min-width:900px}")
        html.append("</style></head><body><div class='container'>")
        html.append("<h1>Projekt-Timeline</h1>")
        html.append("<div class='chart'><div class='scroll'><canvas id='foldersChart' height='200'></canvas></div></div>")
        html.append("<div class='chart'><div class='scroll'><canvas id='filesChart' height='200'></canvas></div></div>")
        html.append("<div class='chart'><div class='scroll'><canvas id='extChart' height='300'></canvas></div></div>")
        payload = {"dates": dates, "folders": [d["folders"] for d in data], "files": [d["total_files"] for d in data], "ext": ext_series}
        html.append("<script>const timelineData = " + json.dumps(payload, ensure_ascii=False) + ";</script>")
        # minimal chart drawing without external libs
        html.append("<script>")
        html.append("""
function drawLineChart(canvasId, labels, series, color){
  const c=document.getElementById(canvasId); const ctx=c.getContext('2d');
  const W = Math.max(labels.length*40, c.clientWidth); const H=c.height;
  c.width = W;
  const pad=30; const maxVal=Math.max(...series,1); const minVal=Math.min(...series,0);
  const yMin=0; const yMax=maxVal;
  ctx.clearRect(0,0,W,H); ctx.strokeStyle='#eee'; ctx.lineWidth=1;
  for(let i=0;i<=5;i++){ const y=pad + (H-2*pad)*i/5; ctx.beginPath(); ctx.moveTo(pad,y); ctx.lineTo(W-pad,y); ctx.stroke(); }
  ctx.strokeStyle=color; ctx.lineWidth=2; ctx.beginPath();
  series.forEach((v,idx)=>{ const x=pad + idx*((W-2*pad)/Math.max(labels.length-1,1)); const y=H-pad - ((v-yMin)/(yMax-yMin))* (H-2*pad); if(idx===0) ctx.moveTo(x,y); else ctx.lineTo(x,y); });
  ctx.stroke();
  ctx.fillStyle='#666'; ctx.font='12px system-ui';
  labels.forEach((lb,idx)=>{ const x=pad + idx*((W-2*pad)/Math.max(labels.length-1,1)); ctx.save(); ctx.translate(x, H-8); ctx.rotate(-Math.PI/4); ctx.fillText(lb, 0,0); ctx.restore(); });
}
function drawStackedChart(canvasId, labels, extData){
  const c=document.getElementById(canvasId); const ctx=c.getContext('2d');
  const keys=Object.keys(extData); const W=Math.max(labels.length*40, c.clientWidth); const H=c.height; c.width=W;
  const pad=30; const totals = labels.map((_,i)=> keys.reduce((s,k)=> s+(extData[k][i]||0),0)); const maxVal=Math.max(...totals,1);
  ctx.clearRect(0,0,W,H);
  const colors=['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd','#8c564b','#e377c2','#7f7f7f','#bcbd22','#17becf'];
  labels.forEach((lb,idx)=>{
    const x=pad + idx*((W-2*pad)/Math.max(labels.length-1,1)); const barW=Math.max(6,(W-2*pad)/labels.length*0.6);
    let yBase=H-pad;
    keys.forEach((k,ki)=>{
      const v=extData[k][idx]||0; const h=((v)/(maxVal))* (H-2*pad);
      ctx.fillStyle=colors[ki%colors.length];
      ctx.fillRect(x-barW/2, yBase-h, barW, h);
      yBase -= h;
    });
  });
  ctx.fillStyle='#666'; ctx.font='12px system-ui';
  labels.forEach((lb,idx)=>{ const x=pad + idx*((W-2*pad)/Math.max(labels.length-1,1)); ctx.save(); ctx.translate(x, H-8); ctx.rotate(-Math.PI/4); ctx.fillText(lb, 0,0); ctx.restore(); });
}
drawLineChart('foldersChart', timelineData.dates, timelineData.folders, '#1f77b4');
drawLineChart('filesChart', timelineData.dates, timelineData.files, '#ff7f0e');
drawStackedChart('extChart', timelineData.dates, timelineData.ext);
""")
        html.append("</script></div></body></html>")
        return "".join(html)
    timeline_html = render_timeline_html(hist)
    (OUT_DIR / "Projectstructure" / "project_metrics_timeline.html").write_text(timeline_html, encoding="utf-8")
    paths = scan_paths(ROOT)
    paths_out = PATHS_DIR / f"{date_str}_paths.json"
    paths_out.write_text(json.dumps({"date": date_str, "entries": paths}, ensure_ascii=False, indent=2), encoding="utf-8")
    counts_json = DAILY_DIR / f"{date_str}_filemetrics.json"
    counts_json.write_text(json.dumps({"date": date_str, "folders": folders, "total_files": sum(counts.values()), "extensions": counts}, ensure_ascii=False), encoding="utf-8")
    print(str(detailed_name))
    print(str(metrics_html_name))
    print(str(history_csv))
    print(str(paths_out))

if __name__ == "__main__":
    main()
