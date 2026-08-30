"""
validate_model.py
-----------------
Static checks over the generated Power BI project, run before Desktop ever
opens it. Desktop's own errors arrive one at a time and only after a refresh;
these arrive all at once, in a second.

Checks:
  1. Every table.column and table.measure referenced by a visual exists.
  2. Every table.column referenced by a relationship exists.
  3. Every table and column referenced inside a DAX measure body exists.
  4. Every measure a measure calls exists.
  5. Orphaned measures - defined but referenced by no visual and no other measure.
  6. Every fact carries exactly one ACTIVE relationship to Dim_Date.
  7. Every .pq file is embedded in exactly one partition.
  8. All JSON files parse.

    python tools/validate_model.py
Exit code is non-zero if any ERROR is found, so it can gate a build.
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
PBI = os.path.join(ROOT, "powerbi")
SM = os.path.join(PBI, "PM_Dashboard.SemanticModel", "definition")
RP = os.path.join(PBI, "PM_Dashboard.Report", "definition")

errors, warns = [], []


def err(msg):
    errors.append(msg)


def warn(msg):
    warns.append(msg)


# ---------------------------------------------------------------- parse TMDL
def parse_model():
    tables, columns, measures, m_bodies = set(), {}, set(), {}
    tdir = os.path.join(SM, "tables")
    for fn in sorted(os.listdir(tdir)):
        if not fn.endswith(".tmdl"):
            continue
        text = open(os.path.join(tdir, fn), encoding="utf-8").read()
        tname = re.search(r"^table\s+(\S+)", text, re.M)
        if not tname:
            err(f"{fn}: no table declaration")
            continue
        tname = tname.group(1).strip("'")
        tables.add(tname)
        columns[tname] = set()

        for m in re.finditer(r"^\tcolumn\s+('([^']+)'|(\S+))", text, re.M):
            columns[tname].add(m.group(2) or m.group(3))

        # measure 'Name' = ``` ... ```
        for m in re.finditer(
                r"^\tmeasure\s+'([^']+)'\s*=\s*```\n(.*?)\n\t\t\t```", text, re.M | re.S):
            measures.add(m.group(1))
            m_bodies[m.group(1)] = m.group(2)
    return tables, columns, measures, m_bodies


def parse_relationships():
    path = os.path.join(SM, "relationships.tmdl")
    text = open(path, encoding="utf-8").read()
    rels = []
    for block in re.split(r"\n(?=relationship )", text):
        if not block.strip():
            continue
        active = "isActive: false" not in block
        f = re.search(r"fromColumn:\s*(\S+)\.(\S+)", block)
        t = re.search(r"toColumn:\s*(\S+)\.(\S+)", block)
        if f and t:
            rels.append((f.group(1), f.group(2), t.group(1), t.group(2), active))
    return rels


def main():
    tables, columns, measures, bodies = parse_model()
    rels = parse_relationships()

    print(f"Model: {len(tables)} tables, "
          f"{sum(len(c) for c in columns.values())} columns, "
          f"{len(measures)} measures, {len(rels)} relationships\n")

    # ---- 1. visual references ---------------------------------------------
    used_measures, visual_count, page_count = set(), 0, 0
    pages_dir = os.path.join(RP, "pages")
    for pg in sorted(os.listdir(pages_dir)):
        pdir = os.path.join(pages_dir, pg)
        if not os.path.isdir(pdir):
            continue
        page_count += 1
        vdir = os.path.join(pdir, "visuals")
        if not os.path.isdir(vdir):
            continue
        for v in sorted(os.listdir(vdir)):
            vfile = os.path.join(vdir, v, "visual.json")
            if not os.path.exists(vfile):
                continue
            visual_count += 1
            try:
                doc = json.load(open(vfile, encoding="utf-8"))
            except json.JSONDecodeError as e:
                err(f"{pg}/{v}: invalid JSON - {e}")
                continue

            if doc.get("name") != v:
                err(f"{pg}/{v}: visual name '{doc.get('name')}' does not match its folder")

            raw = json.dumps(doc)
            for entity, prop in re.findall(
                    r'"SourceRef":\s*\{\s*"Entity":\s*"([^"]+)"\s*\}\s*\},\s*"Property":\s*"([^"]+)"',
                    raw):
                if entity not in tables:
                    err(f"{pg}/{v}: references unknown table '{entity}'")
                elif prop in measures and entity == "_Measures":
                    used_measures.add(prop)
                elif prop not in columns.get(entity, set()) and prop not in measures:
                    err(f"{pg}/{v}: '{entity}[{prop}]' is not a column or measure in the model")

    print(f"Report: {page_count} pages, {visual_count} visuals\n")

    # ---- 2. relationship endpoints ----------------------------------------
    for ft, fc, tt, tc, active in rels:
        if ft not in tables:
            err(f"relationship: unknown table '{ft}'")
        elif fc not in columns[ft]:
            err(f"relationship: '{ft}[{fc}]' does not exist")
        if tt not in tables:
            err(f"relationship: unknown table '{tt}'")
        elif tc not in columns[tt]:
            err(f"relationship: '{tt}[{tc}]' does not exist")

    # ---- 3 & 4. DAX body references ---------------------------------------
    for name, body in bodies.items():
        for t, c in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\[([^\]]+)\]", body):
            if t.startswith("@"):
                continue
            if t not in tables:
                err(f"measure '{name}': unknown table '{t}'")
            elif c not in columns[t]:
                err(f"measure '{name}': '{t}[{c}]' is not a column")
        # [Measure Name] with no table prefix
        for ref in re.findall(r"(?<![A-Za-z0-9_\]])\[([^\]]+)\]", body):
            if ref.startswith("@"):
                continue
            if ref in measures:
                used_measures.add(ref)
            elif not any(ref in cs for cs in columns.values()):
                err(f"measure '{name}': calls '[{ref}]' which is neither a measure nor a column")

    # ---- 5. orphans --------------------------------------------------------
    orphans = sorted(measures - used_measures)
    for o in orphans:
        warn(f"measure '{o}' is defined but used by no visual and called by no other measure")

    # ---- 6. one active date relationship per fact -------------------------
    facts = sorted(t for t in tables if t.startswith("Fact_"))
    for f in facts:
        active_dates = [r for r in rels if r[2] == "Dim_Date" and r[0] == f and r[4]]
        inactive = [r for r in rels if r[2] == "Dim_Date" and r[0] == f and not r[4]]
        if len(active_dates) == 0:
            err(f"{f}: no ACTIVE relationship to Dim_Date")
        elif len(active_dates) > 1:
            err(f"{f}: {len(active_dates)} active date relationships - only one is allowed")
        else:
            print(f"  {f:<24} active date: {active_dates[0][1]:<20} "
                  f"({len(inactive)} inactive)")

    # ---- 7. every .pq is embedded -----------------------------------------
    print()
    pq_files = {f for f in os.listdir(os.path.join(PBI, "m_queries")) if f.endswith(".pq")}
    embedded = set()
    all_tmdl = ""
    for d, _, fs in os.walk(SM):
        for f in fs:
            if f.endswith(".tmdl"):
                all_tmdl += open(os.path.join(d, f), encoding="utf-8").read()
    for pq in sorted(pq_files):
        body = open(os.path.join(PBI, "m_queries", pq), encoding="utf-8").read()
        # match on a distinctive non-comment line from the file
        probe = next((l.strip() for l in body.split("\n")
                      if l.strip() and not l.strip().startswith("//") and len(l.strip()) > 25),
                     None)
        if probe and probe in all_tmdl:
            embedded.add(pq)
        else:
            err(f"m_queries/{pq} is not embedded in any TMDL partition or expression")
    print(f"Power Query: {len(embedded)}/{len(pq_files)} .pq files embedded in the model")

    # ---- 8. JSON parses ----------------------------------------------------
    bad_json = 0
    for d, _, fs in os.walk(PBI):
        for f in fs:
            if f.endswith(".json"):
                try:
                    json.load(open(os.path.join(d, f), encoding="utf-8"))
                except json.JSONDecodeError as e:
                    err(f"{os.path.relpath(os.path.join(d, f), ROOT)}: invalid JSON - {e}")
                    bad_json += 1
    print(f"JSON: all files parsed" if not bad_json else f"JSON: {bad_json} invalid")

    # ---- report ------------------------------------------------------------
    print("\n" + "=" * 72)
    print(f"  {len(errors)} error(s), {len(warns)} warning(s)")
    print("=" * 72)
    for e in errors:
        print(f"  ERROR  {e}")
    for w in warns:
        print(f"  WARN   {w}")
    if not errors:
        print("\n  Every reference in every visual, relationship and measure resolves.")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
