#!/usr/bin/env python3
"""
check_consistency.py
--------------------
One command that proves the deliverable agrees with itself.

Everything here is derived from a generated source of truth - the schema module,
the exported CSVs, the built model, the DAX - and compared against what the
documents claim. A document that has drifted from the thing it describes is
worse than no document, because it is believed.

    python tools/check_consistency.py

Exit code 0 means every check passed. Anything else is a real inconsistency and
the output names the file and the line.
"""
import csv, glob, json, os, re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import essential_schema as es                                   # noqa: E402

FAILS = []


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   {detail}" if detail else ""))
    if not ok:
        FAILS.append(label)


def read(rel):
    return (ROOT / rel).read_text(errors="ignore")


def docs():
    """Every document we author. The supplied inputs are a record, not ours to edit."""
    return {str(p.relative_to(ROOT)): p.read_text(errors="ignore")
            for p in ROOT.rglob("*.md")
            if not {"​.git", "node_modules", "input"} & set(p.parts)
            and ".git" not in p.parts and "node_modules" not in p.parts
            and "input" not in p.parts}


def main():
    D = docs()
    allmd = "\n".join(D.values())

    # ---------------------------------------------------------------- schema
    print("\nSchema")
    kept = {c for cols in es.KEEP.values() for c in cols}
    n_lists, n_cols = len(es.KEEP), sum(len(v) for v in es.KEEP.values())

    sch = {p.stem: json.loads(p.read_text())
           for p in (ROOT / "sharepoint/schema").glob("*.json") if p.stem != "_manifest"}
    check("schema files match essential_schema",
          len(sch) == n_lists and all(
              [f["InternalName"] for f in d["Fields"]] == es.KEEP[d["ListTitle"]]
              for d in sch.values()),
          f"{n_lists} lists, {n_cols} columns")

    check("every field's internal name equals its display name",
          all(f["InternalName"] == f["DisplayName"]
              for d in sch.values() for f in d["Fields"]),
          "otherwise SharePoint mangles them to Cell_x005f_ID")

    csvs = {os.path.basename(f)[:-4]: next(csv.reader(open(f, encoding="utf-8-sig")))
            for f in glob.glob(str(ROOT / "sharepoint/data/*.csv"))
            if not os.path.basename(f).startswith("_")}
    check("exported CSV headers match the schema",
          all(csvs.get(l) == cols for l, cols in es.KEEP.items()),
          f"{len(csvs)} files")

    # An unindexed filter works fine until the list passes 5,000 items, then fails
    # silently and years later. Derive the requirement rather than trusting a list.
    view_defs = json.loads(read("sharepoint/views/_views.json"))["Views"]
    gaps = []
    for v in view_defs:
        d = sch.get(v["List"])
        if not d:
            continue
        idx = set(d["IndexedColumns"])
        cols = {f["InternalName"] for f in d["Fields"]}
        for c in re.findall(r"<FieldRef Name='([^']+)'", v.get("Query", "")):
            if c in cols and c not in idx:
                gaps.append(f"{v['List']}.{c} (view '{v['Title']}')")
    check("every column a view filters on is indexed", not gaps,
          "; ".join(gaps[:3]) if gaps else "no 5,000-item threshold risk")

    check("no list exceeds SharePoint's 20-index limit",
          all(len(d["IndexedColumns"]) <= 20 for d in sch.values()),
          f"{sum(len(d['IndexedColumns']) for d in sch.values())} indexes across {len(sch)} lists")

    check("the daily digest's reset-failure query is indexed",
          "Reset_Applied" in sch["PM_WorkOrder"]["IndexedColumns"],
          "the one silent failure that costs most")

    # Masters must load before the lists whose foreign keys point at them.
    order = json.loads(read("sharepoint/schema/_manifest.json"))["ProvisioningOrder"]
    check("the manifest orders every list", set(order) == set(es.KEEP), f"{len(order)} lists")
    pos = {n: i for i, n in enumerate(order)}
    PARENTS = {
        "Machine_Master": ["Cell_Master"], "StdHours_Monthly": ["Cell_Master"],
        "PM_WorkOrder": ["Cell_Master"],
        "PM_Machine_Task": ["PM_WorkOrder", "Machine_Master"],
        "Checklist_Response": ["PM_WorkOrder", "Machine_Master", "Checklist_Master"],
        "Breakdown_Log": ["Machine_Master", "Technician_Master"],
        "Spare_Replaced": ["Machine_Master", "Spare_Master"],
        "Abnormality_Log": ["Machine_Master"], "PM_Plan_Calendar": ["Cell_Master"],
    }
    bad = [f"{c} before {p}" for c, ps in PARENTS.items() for p in ps
           if c in pos and p in pos and pos[p] > pos[c]]
    check("every list loads after the masters it references", not bad, str(bad) if bad else "")

    # ---------------------------------------------------------------- counts in prose
    print("\nCounts quoted in the documents")
    rows = list(csv.DictReader(open(ROOT / "sharepoint/data/_ROW_COUNTS.csv",
                                    encoding="utf-8-sig")))
    total_rows = sum(int(r["Row_Count"]) for r in rows)

    tmdl = "\n".join(p.read_text() for p in
                     (ROOT / "powerbi/PM_Dashboard.SemanticModel/definition").rglob("*.tmdl"))
    measures = set(re.findall(r"^\tmeasure '([^']+)'", tmdl, re.M)) | \
               set(re.findall(r"^\tmeasure ([A-Za-z_][A-Za-z0-9_]*)\s*=", tmdl, re.M))
    tables = len(list((ROOT / "powerbi/PM_Dashboard.SemanticModel/definition/tables").glob("*.tmdl")))
    pq = len(list((ROOT / "powerbi/m_queries").glob("*.pq")))
    views = len(json.loads(read("sharepoint/views/_views.json"))["Views"])
    fmt = len(list((ROOT / "sharepoint/formatting").glob("*.json")))
    flows = len(re.findall(r"^# Flow \d+ —", read("automate/FLOW_SPECS.md"), re.M))
    forms = len(re.findall(r"^## Form \d+ —", read("automate/FLOW_SPECS.md"), re.M))
    uat = len(re.findall(r"^### UAT-", read("docs/UAT_TEST_CASES.md"), re.M))

    # A number is only wrong if it is not one of the true values for that noun.
    # Several are legitimately different facts: 85 measures exist in the model,
    # the verifier independently recomputes 65 of them, and both get quoted.
    n_cut = len(es.CUT)
    verifier_labels = len(set(re.findall(
        r'record\(\s*"[^"]+",\s*"([^"]+)"', read("tools/verify_measures.py"))))

    ALLOWED = {
        "lists":    {n_lists, n_lists + len(es.DROP_LISTS)},
        "columns":  {n_cols, n_cut, n_cols + n_cut + 28},   # now, cut, and the original
        "measures": {len(measures), verifier_labels},
        "flows":    {flows, 11},                            # 11 is the pre-reduction count
        "cases":    {uat},
        "views":    {views},
    }
    for noun, ok_values in ALLOWED.items():
        hits = []
        for name, text in D.items():
            for i, line in enumerate(text.splitlines(), 1):
                # (?<!§) so "§9 lists all 65 measures" is not read as a claim
                # that there are nine lists.
                for found in re.findall(rf"(?<!§)\b(\d+) {noun}\b", line):
                    if int(found) not in ok_values:
                        hits.append(f"{name}:{i} says {found} {noun}")
        check(f"every '<n> {noun}' in the documents is a real figure",
              not hits, "; ".join(hits[:3]) if hits else f"true values: {sorted(ok_values)}")

    hits = []
    for name, text in D.items():
        for i, line in enumerate(text.splitlines(), 1):
            for found in re.findall(r"\b(\d,\d\d\d) rows\b", line):
                if found != f"{total_rows:,}":
                    hits.append(f"{name}:{i} says {found}")
    check("every row total in the documents matches the export", not hits,
          "; ".join(hits[:3]) if hits else f"{total_rows:,} rows")

    check("view and formatting files match what the docs claim",
          f"{views} views" in allmd and f"{fmt} column-formatting" in allmd,
          f"{views} views, {fmt} formatting files")
    check("Power Query file count is stated correctly",
          f"{pq} commented Power Query" in allmd, f"{pq} .pq files")
    check("the build sheet defines one section per form and per flow",
          forms == 5 and flows == 9, f"{forms} forms, {flows} flows")

    # ---------------------------------------------------------------- nothing removed survives
    print("\nRemoved columns and lists")
    cut = {k.split(".", 1)[1] for k in es.CUT} - kept
    gone = cut | set(es.DROP_LISTS)
    # Power Query legitimately CREATES these; the list no longer stores them.
    DERIVED = {"Duration_Min", "Completion_Date", "Total_Cost_INR", "MTTR_Min",
               "Response_Time_Min", "Actual_Start_Date", "Actual_End_Date",
               "PM_Duration_Min"}

    pqtext = " ".join(p.read_text() for p in (ROOT / "powerbi/m_queries").glob("*.pq"))
    hits = sorted(g for g in gone - DERIVED if re.search(rf'"{re.escape(g)}"', pqtext))
    check("Power Query reads no removed column", not hits, str(hits) if hits else "")

    ps = " ".join(p.read_text() for p in (ROOT / "sharepoint").glob("*.ps1"))
    hits = sorted(g for g in gone if re.search(rf"""['"\[]{re.escape(g)}['"\]]""", ps))
    check("PowerShell names no removed column or list", not hits, str(hits) if hits else "")

    # In the flow docs, only INSTRUCTIONS matter - the "what came out" notes name
    # removed columns on purpose, and should.
    instr, inside = "", False
    for f in ("automate/FLOW_SPECS.md", "automate/expressions.md"):
        for line in read(f).splitlines():
            if line.startswith("```"):
                inside = not inside
                continue
            if inside or line.startswith("| `") or line.startswith("      | `"):
                instr += line + "\n"
    hits = sorted(g for g in gone if re.search(rf"\b{re.escape(g)}\b", instr))
    check("flow instructions name no removed column or list", not hits, str(hits) if hits else "")

    refs = set(re.findall(r"\[\$([A-Za-z_][A-Za-z0-9_]*)\]",
                          " ".join(p.read_text() for p in
                                   list((ROOT / "sharepoint/views").glob("*.json")) +
                                   list((ROOT / "sharepoint/formatting").glob("*.json")))))
    check("every view/format column reference exists", not (refs - kept),
          str(sorted(refs - kept)) if refs - kept else f"{len(refs)} refs")

    # ---------------------------------------------------------------- names line up
    print("\nNames and identifiers")
    dd = read("docs/DATA_DICTIONARY.md")
    check("data dictionary documents every column exactly once",
          len(re.findall(r"^\| `[A-Za-z_][A-Za-z0-9_]*` \|", dd, re.M)) == n_cols,
          f"{n_cols} rows")

    verifier = read("tools/verify_measures.py")
    labels = set(re.findall(r'record\(\s*"[^"]+",\s*"([^"]+)"', verifier))
    check("every verifier row label names a real measure",
          not (labels - measures), str(sorted(labels - measures)[:3]) if labels - measures else
          f"{len(labels)} labels")

    uat_defined = set(re.findall(r"^### (UAT-[0-9a-z]+)", read("docs/UAT_TEST_CASES.md"), re.M))
    uat_cited = set(re.findall(r"\b(UAT-\d+[a-z]?)\b", allmd))
    check("every UAT case cited is defined", not (uat_cited - uat_defined),
          str(sorted(uat_cited - uat_defined)) if uat_cited - uat_defined else f"{len(uat_defined)} cases")

    view_names = {v["Title"] for v in json.loads(read("sharepoint/views/_views.json"))["Views"]}
    cited = {a or b for a, b in re.findall(r"\*\*([A-Z][A-Za-z0-9 ]+)\*\* view|`([A-Z][A-Za-z0-9 ]+)` view", allmd)}
    check("every view named in the docs is provisioned", not (cited - view_names),
          str(sorted(cited - view_names)) if cited - view_names else f"{len(view_names)} views")

    nums = {int(x) for x in re.findall(r"\bFlow (\d+)\b", allmd)} | \
           {int(x) for x in re.findall(r"\bPM-(\d\d)\b", allmd)}
    check("no document references a flow number that no longer exists",
          nums <= set(range(1, flows + 1)), f"referenced: {sorted(nums)}")

    # ---------------------------------------------------------------- paths resolve
    print("\nFile references")
    rx = re.compile(r"`([A-Za-z0-9_./\\-]+\.(?:py|ps1|js|md|json|pq|dax|pbip|csv|xlsx|pptx|docx|pdf|txt))`")
    missing = []
    for name, text in D.items():
        for m in rx.finditer(text):
            ref = m.group(1)
            if ref.startswith(("http", "C:", "~", "$")):
                continue
            norm = ref.replace("\\", "/")
            if (ROOT / norm).exists() or (ROOT / name).parent.joinpath(norm).exists():
                continue
            if list(ROOT.rglob(pathlib.Path(norm).name)):
                continue
            missing.append(f"{name} -> {ref}")
    check("every path the documents tell you to open exists", not missing,
          "; ".join(missing[:3]) if missing else "")

    # ---------------------------------------------------------------- BUILD.md
    # The build guide is the one document a reader follows literally, so its
    # claims are checked hardest.
    print("\nBUILD.md")
    build = read("BUILD.md")
    main_part = build.split('<a name="appendix-a"></a>')[0]

    py_cmds = re.findall(r"^(?:python3?|pip) .*", main_part, re.M)
    check("the main build path names no Python command", not py_cmds,
          str(py_cmds[:2]) if py_cmds else "Python is confined to the appendix")

    ps_used = sorted(set(re.findall(r"\.\\(\w+\.ps1)", build)))
    missing_ps = [n for n in ps_used if not (ROOT / "sharepoint" / n).exists()]
    check("every PowerShell script the build runs exists", not missing_ps,
          str(missing_ps) if missing_ps else ", ".join(ps_used))

    no_clientid = [n for n in ps_used
                   if "[string]$ClientId" not in (ROOT / "sharepoint" / n).read_text()]
    check("every script the build runs accepts -ClientId", not no_clientid,
          str(no_clientid) if no_clientid else "blocked-tenant path works throughout")

    anchors = set(re.findall(r'<a name="([^"]+)">', build))
    links = set(re.findall(r"\]\(#([a-z0-9\-]+)\)", build))
    check("every internal link in BUILD.md has an anchor", links <= anchors,
          str(sorted(links - anchors)) if links - anchors else f"{len(links)} links")

    check("the browser QR page and its two files are present",
          all((ROOT / "qr/browser" / f).exists()
              for f in ("qr_labels.html", "machines.js", "qrcode.js")),
          "the no-install sticker path")

    # The browser machine list and Machine_Master must not drift apart.
    mjs = read("qr/browser/machines.js")
    js_ids = re.findall(r'"id":\s*"([^"]+)"', mjs)
    declared = re.search(r"MACHINE_COUNT_EXPECTED\s*=\s*(\d+)", mjs)
    active = [r["Machine_ID"] for r in csv.DictReader(
        open(ROOT / "sharepoint/data/Machine_Master.csv", encoding="utf-8-sig"))
        if r["Active"] == "Yes"]
    check("the browser machine list matches Machine_Master", js_ids == active,
          f"{len(js_ids)} machines" if js_ids == active else "lists differ")
    check("machines.js declares its own length correctly",
          bool(declared) and int(declared.group(1)) == len(js_ids),
          f"MACHINE_COUNT_EXPECTED = {declared.group(1) if declared else '?'}")

    # ---------------------------------------------------------------- PowerShell
    # pwsh is not always available to run these, so check statically what can be.
    print("\nPowerShell scripts")
    ps_files = {f.name: f.read_text() for f in sorted((ROOT / "sharepoint").glob("*.ps1"))}

    unbalanced = []
    for name, txt in ps_files.items():
        t = re.sub(r"@[\"']. *?[\"']@", "", txt, flags=re.S)
        t = re.sub(r"(?m)#.*$", "", t)
        t = re.sub(r"'[^'\n]*'", "''", t)
        t = re.sub(r'"[^"\n]*"', '""', t)
        for o, c in (("{", "}"), ("(", ")"), ("[", "]")):
            if t.count(o) != t.count(c):
                unbalanced.append(f"{name} {o}{c} {t.count(o) - t.count(c):+d}")
    check("brackets balance in every script", not unbalanced,
          "; ".join(unbalanced) if unbalanced else f"{len(ps_files)} scripts")

    # Any Write-Something that is neither a PowerShell built-in nor defined in the
    # file is a typo that only surfaces at runtime, halfway through provisioning.
    BUILTIN = {"Write-Host", "Write-Output", "Write-Error", "Write-Warning",
               "Write-Verbose", "Write-Debug", "Write-Information", "Write-Progress"}
    bad = []
    for name, txt in ps_files.items():
        defined = set(re.findall(r"^function\s+([A-Za-z][\w-]*)", txt, re.M))
        called = set(re.findall(r"\b(Write-[A-Za-z][\w]*)\b", txt))
        bad += [f"{name}:{c}" for c in sorted(called - defined - BUILTIN)]
    check("every Write-* a script calls is a built-in or defined in it", not bad,
          "; ".join(bad) if bad else f"{len(ps_files)} scripts")

    # Only the scripts that CHANGE the tenant need -WhatIf; requiring it on a
    # read-only one would be noise, and would hide the thing worth checking -
    # that the read-only one really is read-only.
    WRITERS = {"provision_lists.ps1", "apply_views.ps1", "load_data.ps1"}
    READONLY = {"verify_load.ps1"}
    no_whatif = [n for n in WRITERS if "SupportsShouldProcess = $true" not in ps_files.get(n, "")]
    check("every script that changes the tenant supports -WhatIf", not no_whatif,
          str(no_whatif) if no_whatif else ", ".join(sorted(WRITERS)))

    MUTATING = r"\b(?:New|Set|Add|Remove|Invoke)-PnP\w+"
    writes = [n for n in READONLY if re.search(MUTATING, ps_files.get(n, ""))]
    check("the verification script only reads", not writes,
          str(writes) if writes else "verify_load.ps1 cannot change anything it checks")

    check("every script accepts -ClientId",
          all(re.search(r"\[string\]\$ClientId", t) and "$connect.ClientId = $ClientId" in t
              for t in ps_files.values()),
          "tenants that block the default PnP app need their own registration")

    ld = ps_files["load_data.ps1"]
    check("load_data.ps1 types the date-format array as [string[]]",
          bool(re.search(r"\[string\[\]\]\$formats\s*=", ld)),
          "a bare @() binds the single-format TryParseExact overload and every date fails")
    check("load_data.ps1 flushes the final partial batch",
          "$null -ne $batch -and $inBatch -gt 0" in ld,
          "otherwise the last rows under one batch are dropped silently")

    prov = ps_files["provision_lists.ps1"]
    types_used = {f["Type"] for d in sch.values() for f in d["Fields"]}
    # The field-XML builder switches on the column type; each arm opens with 'Type' {
    m = re.search(r"switch\s*\(\s*\$Field\.Type\s*\)\s*\{", prov)
    handled = set()
    if m:
        handled = set(re.findall(r"^\s{8}'([A-Za-z]+)'\s*\{", prov[m.end():], re.M))
    check("provision_lists.ps1 handles every column type the schema uses",
          bool(handled) and types_used <= handled,
          f"handles {sorted(handled)}" if handled and types_used <= handled
          else f"switch not found" if not handled
          else f"UNHANDLED: {sorted(types_used - handled)}")

    # ---------------------------------------------------------------- forms script
    # The forms script is typed into Microsoft Forms by hand. If it drifts from
    # Checklist_Master, the limit on the phone stops matching the limit in the
    # system - and a machine passes against the wrong number with nothing to catch it.
    print("\nForms build script")
    fs = read("automate/FORMS_BUILD_SCRIPT.md")
    cl = [r for r in csv.DictReader(
        open(ROOT / "sharepoint/data/Checklist_Master.csv", encoding="utf-8-sig"))
        if r["Active"] == "Yes"]

    missing = [c["Check_Point"] for c in cl if c["Check_Point"] not in fs]
    check("every check point appears verbatim", not missing,
          str(missing[:2]) if missing else f"{len(cl)} check points")

    bad_std = [c["Acceptance_Standard"] for c in cl
               if f"Accept: {c['Acceptance_Standard']}" not in fs]
    check("every acceptance standard appears verbatim", not bad_std,
          str(bad_std[:2]) if bad_std else "the limit on the phone matches the list")

    wrong_type = [f"{c['Checklist_ID']}/{c['Item_No']}" for c in cl
                  if (("Reading — " if c["Check_Type"] == "Measurement"
                       else "Observation — ") + c["Check_Point"]) not in fs]
    check("measurement items ask for a number, others for an observation",
          not wrong_type, str(wrong_type[:2]) if wrong_type else "")

    crit = sum(1 for c in cl if c["Safety_Critical"] == "Yes")
    check("every safety-critical item is flagged",
          fs.count("SAFETY-CRITICAL") == crit,
          f"{crit} of {len(cl)} block the cell from closing")

    ids = {c["Checklist_ID"] for c in cl}
    check("one branched section per checklist",
          len(re.findall(r"^## Section \d+ — `", fs, re.M)) == len(ids),
          f"{len(ids)} sections")

    names = [t["Tech_Name"] for t in csv.DictReader(
        open(ROOT / "sharepoint/data/Technician_Master.csv", encoding="utf-8-sig"))
        if t["Active"] == "Yes"]
    check("every active technician is in the dropdowns",
          all(n in fs for n in names), f"{len(names)} names")

    codes = [sp["Spare_Code"] for sp in csv.DictReader(
        open(ROOT / "sharepoint/data/Spare_Master.csv", encoding="utf-8-sig"))
        if sp["Active"] == "Yes"]
    check("every active spare code is listed", all(c in fs for c in codes),
          f"{len(codes)} codes")

    # ---------------------------------------------------------------- label language
    # The plant asked for English-only stickers. Both generators and the shop-floor
    # SOP have to agree on that, and a stray Tamil string in one of them would print
    # thirty times before anyone noticed.
    print("\nSticker and SOP language")
    tamil = re.compile("[\u0B80-\u0BFF]")
    offenders = []
    for f in ROOT.rglob("*"):
        if not f.is_file() or {"node_modules", ".git", "input"} & set(f.parts):
            continue
        if f.suffix.lower() in (".png", ".pdf", ".xlsx", ".docx", ".pptx"):
            continue
        try:
            body = f.read_text(errors="ignore")
        except OSError:
            continue
        for i, line in enumerate(body.splitlines(), 1):
            if tamil.search(line):
                offenders.append(f"{f.relative_to(ROOT)}:{i}")
    check("no deliverable carries a second-language string", not offenders,
          "; ".join(offenders[:4]) if offenders else "English only, as asked")

    # Both label generators must print the same instruction, or the two paths
    # produce different stickers for the same machine.
    py_line = re.search(r'ENGLISH_LINE\s*=\s*"([^"]*)"', read("qr/generate_qr_labels.py"))
    js_line = re.search(r'var ENGLISH\s*=\s*"([^"]*)"', read("qr/browser/qr_labels.html"))
    check("both label generators print the same instruction",
          bool(py_line) and bool(js_line) and py_line.group(1) == js_line.group(1),
          repr(py_line.group(1)) if py_line else "not found")

    # ---------------------------------------------------------------- the constraint
    print("\nDelivery constraint")
    banned = re.compile(r"\bclaude\b|\banthropic\b|\bchatgpt\b|\bcopilot\b|\bllm\b|"
                        r"\bgenerative ai\b|\bAI[- ]generated\b", re.I)
    offenders = []
    for p in ROOT.rglob("*"):
        if not p.is_file() or {"node_modules", ".git", "input"} & set(p.parts):
            continue
        if p.suffix.lower() in (".md", ".py", ".ps1", ".js", ".json", ".pq", ".dax",
                                ".txt", ".tmdl", ".pbip", ".platform", ""):
            for i, line in enumerate(p.read_text(errors="ignore").splitlines(), 1):
                if banned.search(line):
                    # "Microsoft Copilot" as a product the reader may meet is allowed.
                    if re.search(r"microsoft copilot|copilot (?:studio|for)", line, re.I):
                        continue
                    offenders.append(f"{p.relative_to(ROOT)}:{i}")
    check("no deliverable mentions an AI tool or vendor", not offenders,
          "; ".join(offenders[:4]) if offenders else "checked every text file")

    # ---------------------------------------------------------------- verdict
    print("\n" + "=" * 70)
    if FAILS:
        print(f"  {len(FAILS)} INCONSISTENCY(IES): {', '.join(FAILS)}")
        print("=" * 70)
        return 1
    print("  Everything agrees. Schema, data, model, flows, views and documents.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
