#!/usr/bin/env python3
"""
build_qr_tool.py - builds QR_Generator.html: a single self-contained page that
regenerates every machine and technician QR code, with no install and no network.

The QR encoder inlined into it is verified module-for-module against the
python-qrcode reference by scripts/qrjs/build_and_test.py before it is embedded.
"""
from __future__ import annotations
import csv, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

print("  verifying the QR encoder ...")
r = subprocess.run([sys.executable, os.path.join(HERE, "qrjs", "build_and_test.py"),
                    "--fuzz", "120"], capture_output=True, text=True)
sys.stdout.write("".join("    " + l + "\n" for l in r.stdout.strip().split("\n")))
if r.returncode != 0:
    sys.exit("  encoder verification FAILED - not embedding an unverified encoder")

encoder = open(os.path.join(HERE, "qrjs", "qr.built.js"), encoding="utf-8").read()

def rows(name):
    with open(os.path.join(ROOT, "data", "dummy", name), encoding="utf-8") as f:
        return list(csv.DictReader(f))

machines = [{k: m[k] for k in ("MachineID", "MachineName", "CellID", "Location",
                               "Criticality", "Make", "Model", "SerialNo",
                               "ChecklistID", "PMStdMinutes")} for m in rows("Machine_Master.csv")]
cells = {c["CellID"]: c["CellName"] for c in rows("Cell_Master.csv")}
for m in machines:
    m["CellName"] = cells.get(m["CellID"], m["CellID"])
techs = [{k: t[k] for k in ("TechID", "TechName", "Shift", "SkillGroup", "PrimaryArea")}
         for t in rows("Technician_Master.csv")]

HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PM QR Code Generator</title>
<style>
:root{
  --ground:#F1F4F5; --surface:#fff; --surface-2:#E8EDEF; --ink:#12262F; --ink-2:#3D5765;
  --ink-3:#6A8391; --rule:#CBD7DD; --accent:#1B6E8C; --accent-soft:#E2EDF1;
  --good:#2F7F66; --warn:#A9701F; --crit:#AE4732;
}
*,*::before,*::after{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);
  font:15px/1.6 "Segoe UI",system-ui,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:0 24px}
header{background:var(--ink);color:#E6EEF1;padding:26px 0}
header h1{margin:0;font-size:1.5rem;letter-spacing:-.02em}
header p{margin:6px 0 0;color:#93AEBA;font-size:.92rem;max-width:80ch}
.panel{background:var(--surface);border:1px solid var(--rule);border-radius:4px;
  padding:22px 24px;margin:22px 0}
.panel h2{margin:0 0 4px;font-size:1.05rem;letter-spacing:-.01em}
.panel .hint{margin:0 0 16px;color:var(--ink-2);font-size:.88rem;max-width:88ch}
.step{display:inline-block;background:var(--accent-soft);color:var(--accent);
  font:600 .68rem/1 ui-monospace,monospace;letter-spacing:.1em;
  padding:5px 8px;border-radius:3px;margin-right:9px;vertical-align:2px}
label{display:block;font-weight:600;font-size:.8rem;margin:0 0 5px;color:var(--ink-2)}
input[type=text],textarea{width:100%;padding:9px 11px;border:1px solid var(--rule);
  border-radius:3px;font:13px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;
  background:var(--surface);color:var(--ink)}
input:focus,textarea:focus{outline:2px solid var(--accent);outline-offset:1px;border-color:var(--accent)}
.grid3{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}
.preview{margin-top:14px;padding:10px 12px;background:var(--surface-2);border-radius:3px;
  font:12px/1.7 ui-monospace,monospace;color:var(--ink-2);word-break:break-all}
.preview b{color:var(--accent)}
button{font:600 .9rem/1 "Segoe UI",sans-serif;padding:11px 20px;border-radius:3px;
  border:1px solid var(--accent);background:var(--accent);color:#fff;cursor:pointer}
button.ghost{background:var(--surface);color:var(--accent)}
button:hover{filter:brightness(1.08)}
button:disabled{opacity:.45;cursor:not-allowed;filter:none}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:16px}
.status{font-size:.86rem;color:var(--ink-2)}
.status.ok{color:var(--good);font-weight:600}
.status.err{color:var(--crit);font-weight:600}
details summary{cursor:pointer;font-weight:600;font-size:.88rem;color:var(--accent);margin-bottom:10px}
/* ---- printable sheets ---- */
#sheets{margin:22px 0 60px}
.sheet{background:#fff;border:1px solid var(--rule);border-radius:4px;padding:10mm;margin-bottom:18px}
.sheet h3{margin:0 0 2mm;font-size:1rem}
.sheet .meta{margin:0 0 6mm;font-size:.8rem;color:var(--ink-3)}
.labels{display:grid;grid-template-columns:repeat(2,1fr);gap:6mm}
.badges{display:grid;grid-template-columns:repeat(3,1fr);gap:6mm}
.card{border:1.5px solid var(--ink);border-radius:3mm;padding:5mm;
  page-break-inside:avoid;break-inside:avoid;background:#fff}
.card .hd{display:flex;justify-content:space-between;gap:3mm;align-items:flex-start;
  border-bottom:1.5px solid var(--ink);padding-bottom:2.5mm;margin-bottom:3mm}
.card .nm{font-size:13pt;font-weight:700;line-height:1.15}
.card .sub{font-size:8pt;color:var(--ink-3);line-height:1.5}
.card .id{font-size:17pt;font-weight:800;color:var(--accent);letter-spacing:.5px;text-align:right}
.card .bd{display:flex;gap:4mm;align-items:center}
.qr{width:34mm;height:34mm;flex:0 0 34mm}
.qr svg{width:100%;height:100%;display:block}
.acts{font-size:8pt;line-height:1.7}
.acts b{display:block;font-size:7.5pt;text-transform:uppercase;letter-spacing:.8px;
  color:var(--accent);margin-bottom:1.5mm}
.acts ul{margin:0;padding-left:4mm}
.ft{margin-top:3mm;padding-top:2mm;border-top:1px dashed var(--rule);
  font-size:7pt;color:var(--ink-3);display:flex;justify-content:space-between;gap:3mm}
.pill{display:inline-block;padding:.8mm 2.5mm;border-radius:10mm;font-size:7.5pt;font-weight:700;
  background:var(--surface-2);color:var(--accent)}
.crit-A{background:#FBE3E0;color:#B4451F}.crit-B{background:#FDF0DC;color:#8A5A16}
.crit-C{background:#E4EDF2;color:#1B6E8C}
.badge{text-align:center}
.badge .qr{width:42mm;height:42mm;margin:0 auto 3mm}
@page{size:A4;margin:10mm}
@media print{
  body{background:#fff}
  header,.panel,#toolbar,.noprint{display:none!important}
  .wrap{max-width:none;padding:0}
  #sheets{margin:0}
  .sheet{border:0;padding:0;margin:0}
  .sheet+.sheet{page-break-before:always}
}
</style></head><body>

<header><div class="wrap">
  <h1>PM QR Code Generator</h1>
  <p>Regenerates every machine and technician QR code for the PM system. Runs entirely
     in this page &mdash; nothing to install, no network connection used, no data leaves the browser.
     Works offline: keep this single file and open it in Edge or Chrome whenever codes need reprinting.</p>
</div></header>

<div class="wrap">

<div class="panel">
  <h2><span class="step">STEP 1</span>Power Apps link</h2>
  <p class="hint">Publish the PM Field App, open <b>Details</b> on the app in Power Apps, and copy the
     <b>Web link</b>. Paste it below and the three IDs are read out of it automatically &mdash;
     or type them in yourself. These IDs change if the app is republished to a
     <em>different environment</em>, and every label must then be reprinted.</p>
  <label for="weblink">Paste the app Web link (easiest)</label>
  <input type="text" id="weblink" spellcheck="false"
         placeholder="https://apps.powerapps.com/play/e/.../a/...?tenantId=...">
  <div class="grid3" style="margin-top:16px">
    <div><label for="env">Environment ID</label><input type="text" id="env" spellcheck="false"></div>
    <div><label for="app">App ID</label><input type="text" id="app" spellcheck="false"></div>
    <div><label for="ten">Tenant ID</label><input type="text" id="ten" spellcheck="false"></div>
  </div>
  <div class="preview" id="linkPreview"></div>
</div>

<div class="panel">
  <h2><span class="step">STEP 2</span>Your machines and technicians</h2>
  <p class="hint">Pre-filled with the sample plant so you can try it immediately. To use your own,
     open <b>Machine_Master.xlsx</b> and <b>Technician_Master.xlsx</b>, select the data rows
     including the header, copy, and paste over the contents below. Column order does not matter;
     the headers are matched by name.</p>
  <details>
    <summary>Machine list &mdash; <span id="mCount"></span></summary>
    <label for="mData">Needs at least MachineID and MachineName. Also uses CellName, Location,
      Criticality, Make, Model, SerialNo, ChecklistID, PMStdMinutes.</label>
    <textarea id="mData" rows="8" spellcheck="false"></textarea>
  </details>
  <details style="margin-top:14px">
    <summary>Technician list &mdash; <span id="tCount"></span></summary>
    <label for="tData">Needs at least TechID and TechName. Also uses Shift, SkillGroup, PrimaryArea.</label>
    <textarea id="tData" rows="6" spellcheck="false"></textarea>
  </details>
  <div class="row">
    <button id="gen">Generate all QR codes</button>
    <button class="ghost" id="print" disabled>Print / save as PDF</button>
    <span class="status" id="status">Enter the app link above, then generate.</span>
  </div>
</div>

</div>

<div class="wrap" id="sheets"></div>

<script>
__ENCODER__
</script>
<script>
(function () {
  "use strict";
  var MACHINES = __MACHINES__;
  var TECHS = __TECHS__;

  var $ = function (id) { return document.getElementById(id); };
  var GUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi;

  function toTsv(rows, cols) {
    return [cols.join("\t")].concat(rows.map(function (r) {
      return cols.map(function (c) { return r[c] === undefined ? "" : r[c]; }).join("\t");
    })).join("\n");
  }
  var M_COLS = ["MachineID","MachineName","CellName","Location","Criticality",
                "Make","Model","SerialNo","ChecklistID","PMStdMinutes"];
  var T_COLS = ["TechID","TechName","Shift","SkillGroup","PrimaryArea"];
  $("mData").value = toTsv(MACHINES, M_COLS);
  $("tData").value = toTsv(TECHS, T_COLS);

  /* Accepts tab-separated (an Excel paste) or comma-separated text. */
  function parse(text) {
    var lines = text.replace(/\r/g, "").split("\n").filter(function (l) { return l.trim() !== ""; });
    if (!lines.length) return [];
    var delim = lines[0].indexOf("\t") >= 0 ? "\t" : ",";
    function cells(line) {
      if (delim === "\t") return line.split("\t");
      var out = [], cur = "", q = false;
      for (var i = 0; i < line.length; i++) {
        var ch = line[i];
        if (ch === '"') { if (q && line[i+1] === '"') { cur += '"'; i++; } else q = !q; }
        else if (ch === "," && !q) { out.push(cur); cur = ""; }
        else cur += ch;
      }
      out.push(cur); return out;
    }
    var head = cells(lines[0]).map(function (h) { return h.trim(); });
    return lines.slice(1).map(function (l) {
      var c = cells(l), o = {};
      head.forEach(function (h, i) { o[h] = (c[i] || "").trim(); });
      return o;
    });
  }

  function ids() {
    return { env: $("env").value.trim(), app: $("app").value.trim(), ten: $("ten").value.trim() };
  }
  function payload(kind, id) {
    var v = ids();
    return "https://apps.powerapps.com/play/e/" + v.env + "/a/" + v.app +
           "?tenantId=" + v.ten + "&source=qr&type=" + kind + "&id=" + id;
  }

  function refreshPreview() {
    var v = ids(), missing = [];
    if (!v.env) missing.push("Environment ID");
    if (!v.app) missing.push("App ID");
    if (!v.ten) missing.push("Tenant ID");
    var p = $("linkPreview");
    if (missing.length) {
      p.innerHTML = "Still needed: <b>" + missing.join("</b>, <b>") + "</b>";
      return false;
    }
    p.innerHTML = "Each machine code will contain:<br>" +
      payload("machine", "MC-001").replace(/&/g, "&amp;")
        .replace(/(MC-001)$/, "<b>$1</b>");
    return true;
  }

  $("weblink").addEventListener("input", function () {
    var found = this.value.match(GUID);
    if (!found) return;
    if (found[0]) $("env").value = found[0];
    if (found[1]) $("app").value = found[1];
    if (found[2]) $("ten").value = found[2];
    refreshPreview();
  });
  ["env","app","ten"].forEach(function (k) {
    $(k).addEventListener("input", refreshPreview);
  });

  function countLabels() {
    $("mCount").textContent = parse($("mData").value).length + " machines";
    $("tCount").textContent = parse($("tData").value).length + " technicians";
  }
  $("mData").addEventListener("input", countLabels);
  $("tData").addEventListener("input", countLabels);
  countLabels();
  refreshPreview();

  var ACTIONS = ["View last PM done date &amp; history", "Start / continue the PM checklist",
                 "Report a breakdown", "Request a spare part",
                 "Record a spare part replaced", "Log an abnormality"];

  function esc(s) {
    return String(s === undefined ? "" : s)
      .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
  }

  function machineCard(m) {
    var crit = (m.Criticality || "C").toUpperCase();
    return '<div class="card"><div class="hd"><div>' +
      '<div class="nm">' + esc(m.MachineName) + '</div>' +
      '<div class="sub">' + esc(m.CellName || m.CellID || "") +
        (m.Location ? " &middot; " + esc(m.Location) : "") + '</div></div>' +
      '<div><div class="id">' + esc(m.MachineID) + '</div>' +
      '<span class="pill crit-' + esc(crit) + '">Criticality ' + esc(crit) + '</span></div></div>' +
      '<div class="bd"><div class="qr">' + QR.toSvg(payload("machine", m.MachineID), 2, "#12262F") + '</div>' +
      '<div class="acts"><b>Scan with your phone camera</b><ul><li>' +
        ACTIONS.join("</li><li>") + '</li></ul></div></div>' +
      '<div class="ft"><span>' + esc(((m.Make || "") + " " + (m.Model || "")).trim()) +
        (m.SerialNo ? " &middot; SN " + esc(m.SerialNo) : "") + '</span>' +
      '<span>' + esc(m.ChecklistID || "") +
        (m.PMStdMinutes ? " &middot; PM " + esc(m.PMStdMinutes) + " min" : "") + '</span></div></div>';
  }

  function techCard(t) {
    return '<div class="card badge"><div class="qr">' +
      QR.toSvg(payload("tech", t.TechID), 2, "#12262F") + '</div>' +
      '<div class="nm">' + esc(t.TechName) + '</div>' +
      '<div class="sub">' + esc(t.TechID) + (t.Shift ? " &middot; " + esc(t.Shift) : "") + '</div>' +
      (t.SkillGroup ? '<div style="margin-top:2mm"><span class="pill">' +
        esc(t.SkillGroup) + '</span></div>' : "") +
      '<div class="ft" style="justify-content:center">Scan to open MY PM LIST</div></div>';
  }

  function chunk(a, n) {
    var out = [];
    for (var i = 0; i < a.length; i += n) out.push(a.slice(i, i + n));
    return out;
  }

  $("gen").addEventListener("click", function () {
    var st = $("status");
    if (!refreshPreview()) { st.className = "status err";
      st.textContent = "Fill in all three IDs first."; return; }
    var machines = parse($("mData").value).filter(function (m) { return m.MachineID; });
    var techs = parse($("tData").value).filter(function (t) { return t.TechID; });
    if (!machines.length && !techs.length) { st.className = "status err";
      st.textContent = "No rows found. Check the pasted data has a header row."; return; }

    st.className = "status"; st.textContent = "Generating…";
    setTimeout(function () {
      var t0 = performance.now(), html = "", n = 0;
      try {
        chunk(machines, 4).forEach(function (page, i) {
          html += '<div class="sheet"><h3>Machine QR Labels</h3>' +
            '<p class="meta">Sheet ' + (i + 1) + ' of ' + Math.ceil(machines.length / 4) +
            ' &middot; print A4 at 100% on polyester or laminated label stock</p>' +
            '<div class="labels">' + page.map(machineCard).join("") + '</div></div>';
          n += page.length;
        });
        chunk(techs, 9).forEach(function (page, i) {
          html += '<div class="sheet"><h3>Technician QR Badges</h3>' +
            '<p class="meta">Sheet ' + (i + 1) + ' of ' + Math.ceil(techs.length / 9) +
            ' &middot; cut and insert into the standard ID card holder, QR facing out</p>' +
            '<div class="badges">' + page.map(techCard).join("") + '</div></div>';
          n += page.length;
        });
      } catch (e) {
        st.className = "status err"; st.textContent = "Failed: " + e.message; return;
      }
      $("sheets").innerHTML = html;
      $("print").disabled = false;
      st.className = "status ok";
      st.textContent = n + " codes generated in " +
        Math.round(performance.now() - t0) + " ms — scroll down, then print.";
    }, 20);
  });

  $("print").addEventListener("click", function () { window.print(); });
})();
</script>
</body></html>
"""

html = (HTML
        .replace("__ENCODER__", encoder)
        .replace("__MACHINES__", json.dumps(machines, ensure_ascii=False))
        .replace("__TECHS__", json.dumps(techs, ensure_ascii=False)))

out = os.path.join(ROOT, "qr", "QR_Generator.html")
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, "w", encoding="utf-8").write(html)
print(f"\n  qr/QR_Generator.html  ({len(html)/1024:.0f} KB, {len(machines)} machines, {len(techs)} technicians)")
