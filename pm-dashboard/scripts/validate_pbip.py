#!/usr/bin/env python3
"""
validate_pbip.py - checks a generated PBIP holds together before Power BI Desktop
sees it. Desktop reports these failures as an unhelpful "couldn't load the report"
or a silently blank visual, so it is worth catching them here.

Checks:
  1. Every JSON file parses.
  2. Every TMDL table has a partition and at least one column.
  3. Every relationship points at a table.column that exists.
  4. Every Entity/Property a visual binds to exists in the model.
  5. Every measure the DAX references (other measures, table[column]) resolves.
  6. Page and visual folder names match the `name` inside their JSON.
  7. Every page listed in pages.json exists on disk, and vice versa.
  8. Every CSV the M layer reads is present in the local data folder.

Run:  python3 scripts/validate_pbip.py [path-to-project-folder]
Exit code 1 if anything fails.
"""

from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NAME = "PM_Dashboard"

BASE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "powerbi")
SM = os.path.join(BASE, f"{NAME}.SemanticModel", "definition")
RP = os.path.join(BASE, f"{NAME}.Report", "definition")

errors: list[str] = []
warnings: list[str] = []
checks = 0


def fail(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


# ---------------------------------------------------------------------------
# 1 · JSON parses
# ---------------------------------------------------------------------------
json_files = []
for root, _d, files in os.walk(BASE):
    for f in files:
        if f.endswith(".json"):
            p = os.path.join(root, f)
            json_files.append(p)
            try:
                with open(p, encoding="utf-8") as fh:
                    json.load(fh)
            except Exception as e:  # noqa: BLE001
                fail(f"invalid JSON: {os.path.relpath(p, BASE)}: {e}")
checks += len(json_files)


# ---------------------------------------------------------------------------
# 2 · Parse the TMDL model
# ---------------------------------------------------------------------------
model: dict[str, set[str]] = {}          # table -> columns
measures: set[str] = set()
measure_dax: dict[str, str] = {}
partitions: set[str] = set()

tables_dir = os.path.join(SM, "tables")
if not os.path.isdir(tables_dir):
    fail(f"no tables folder at {tables_dir}")
    tmdl_files = []
else:
    tmdl_files = sorted(os.listdir(tables_dir))

for fn in tmdl_files:
    if not fn.endswith(".tmdl"):
        continue
    text = open(os.path.join(tables_dir, fn), encoding="utf-8").read()
    m = re.search(r"^table\s+(\S+)", text, re.M)
    if not m:
        fail(f"{fn}: no table declaration")
        continue
    tname = m.group(1).strip("'")
    cols = set(re.findall(r"^\tcolumn\s+(.+)$", text, re.M))
    model[tname] = {c.strip().strip("'") for c in cols}
    if re.search(r"^\tpartition\s+", text, re.M):
        partitions.add(tname)
    else:
        fail(f"{tname}: no partition — the table will load no data")
    if not model[tname]:
        fail(f"{tname}: no columns")
    for mm in re.finditer(r"^\tmeasure\s+'([^']+)'\s*=", text, re.M):
        measures.add(mm.group(1))
    # capture each measure's DAX body for reference checking
    for block in re.finditer(
        r"^\tmeasure\s+'([^']+)'\s*=\s*```\n(.*?)^\t\t\t```", text, re.M | re.S
    ):
        measure_dax[block.group(1)] = block.group(2)

checks += len(model)
if not measures:
    fail("no measures found in the model")


# ---------------------------------------------------------------------------
# 3 · Relationships resolve
# ---------------------------------------------------------------------------
rel_path = os.path.join(SM, "relationships.tmdl")
n_rel = 0
if os.path.exists(rel_path):
    rel_text = open(rel_path, encoding="utf-8").read()
    for kind in ("fromColumn", "toColumn"):
        for ref in re.findall(rf"^\t{kind}:\s*(\S+)\.(\S+)$", rel_text, re.M):
            n_rel += 1
            t, c = ref
            t, c = t.strip("'"), c.strip("'")
            if t not in model:
                fail(f"relationship {kind} references unknown table: {t}")
            elif c not in model[t]:
                fail(f"relationship {kind} references unknown column: {t}[{c}]")
else:
    fail("relationships.tmdl missing")
checks += n_rel


# ---------------------------------------------------------------------------
# 4 · Every visual field reference resolves
# ---------------------------------------------------------------------------
def walk(obj, hits):
    """Collect every {Entity, Property} pair, tagged Measure or Column."""
    if isinstance(obj, dict):
        for kind in ("Measure", "Column"):
            node = obj.get(kind)
            if isinstance(node, dict) and "Property" in node:
                ent = (node.get("Expression", {})
                           .get("SourceRef", {})
                           .get("Entity"))
                if ent:
                    hits.append((kind, ent, node["Property"]))
        for v in obj.values():
            walk(v, hits)
    elif isinstance(obj, list):
        for v in obj:
            walk(v, hits)


pages_dir = os.path.join(RP, "pages")
page_keys_on_disk = set()
n_vis = 0
n_refs = 0

if os.path.isdir(pages_dir):
    for pg in sorted(os.listdir(pages_dir)):
        pdir = os.path.join(pages_dir, pg)
        if not os.path.isdir(pdir):
            continue
        page_keys_on_disk.add(pg)

        pj = os.path.join(pdir, "page.json")
        if not os.path.exists(pj):
            fail(f"{pg}: page.json missing")
            continue
        page = json.load(open(pj, encoding="utf-8"))
        if page.get("name") != pg:
            fail(f"{pg}: page.json name is '{page.get('name')}', must match the folder")

        vdir = os.path.join(pdir, "visuals")
        if not os.path.isdir(vdir):
            warn(f"{pg}: no visuals folder")
            continue
        for vs in sorted(os.listdir(vdir)):
            vf = os.path.join(vdir, vs, "visual.json")
            if not os.path.exists(vf):
                fail(f"{pg}/{vs}: visual.json missing")
                continue
            n_vis += 1
            v = json.load(open(vf, encoding="utf-8"))
            if v.get("name") != vs:
                fail(f"{pg}/{vs}: visual.json name is '{v.get('name')}', "
                     "must match the folder")
            if len(vs) > 50:
                fail(f"{pg}/{vs}: visual name exceeds 50 characters")

            hits: list = []
            walk(v, hits)
            for kind, ent, prop in hits:
                n_refs += 1
                if ent not in model:
                    fail(f"{pg}/{vs}: unknown table '{ent}'")
                elif kind == "Measure":
                    if prop not in measures:
                        fail(f"{pg}/{vs}: unknown measure '{prop}'")
                elif prop not in model[ent]:
                    fail(f"{pg}/{vs}: unknown column {ent}[{prop}]")
else:
    fail("no pages folder in the report")
checks += n_refs


# ---------------------------------------------------------------------------
# 5 · Measure DAX references resolve
# ---------------------------------------------------------------------------
DAX_FUNCS = set()
n_dax = 0
for mname, dax in measure_dax.items():
    body = re.sub(r'"[^"]*"', '""', dax)          # strip string literals
    # table[column]
    for t, c in re.findall(r"(\w+)\[([^\]]+)\]", body):
        n_dax += 1
        if t in model:
            if c not in model[t]:
                fail(f"measure '{mname}': unknown column {t}[{c}]")
        elif not t.startswith("@") and t not in ("VAR",):
            fail(f"measure '{mname}': unknown table '{t}' in {t}[{c}]")
    # [Measure Name] not preceded by a table name or @
    for ref in re.findall(r"(?<![\w\]@])\[([^\]]+)\]", body):
        if ref.startswith("@"):
            continue
        n_dax += 1
        if ref not in measures:
            fail(f"measure '{mname}': references unknown measure [{ref}]")
checks += n_dax


# ---------------------------------------------------------------------------
# 6 · pages.json agrees with what is on disk
# ---------------------------------------------------------------------------
pj = os.path.join(pages_dir, "pages.json")
if os.path.exists(pj):
    meta = json.load(open(pj, encoding="utf-8"))
    order = set(meta.get("pageOrder", []))
    for missing in sorted(order - page_keys_on_disk):
        fail(f"pages.json lists '{missing}' but there is no folder for it")
    for orphan in sorted(page_keys_on_disk - order):
        fail(f"page folder '{orphan}' is not listed in pages.json")
    if meta.get("activePageName") not in order:
        fail("pages.json activePageName is not in pageOrder")
    checks += len(order)
else:
    fail("pages/pages.json missing")


# ---------------------------------------------------------------------------
# 7 · Required project files
# ---------------------------------------------------------------------------
for rel in [f"{NAME}.pbip",
            f"{NAME}.SemanticModel/.platform",
            f"{NAME}.SemanticModel/definition.pbism",
            f"{NAME}.SemanticModel/definition/database.tmdl",
            f"{NAME}.SemanticModel/definition/model.tmdl",
            f"{NAME}.SemanticModel/definition/expressions.tmdl",
            f"{NAME}.Report/.platform",
            f"{NAME}.Report/definition.pbir",
            f"{NAME}.Report/definition/report.json"]:
    checks += 1
    if not os.path.exists(os.path.join(BASE, rel)):
        fail(f"missing project file: {rel}")


# ---------------------------------------------------------------------------
# 7b · $schema of every wrapper file matches what Power BI Desktop accepts.
#      Desktop validates these with a regex per file type and refuses to open the
#      project if one is wrong, naming only the first offender. Values verified
#      against published PBIP projects.
# ---------------------------------------------------------------------------
SCHEMA_RULES = {
    f"{NAME}.pbip":
        r"^https://developer\.microsoft\.com/json-schemas/fabric/pbip/"
        r"pbipProperties/1\.\d+\.\d+/schema\.json$",
    f"{NAME}.SemanticModel/.platform":
        r"^https://developer\.microsoft\.com/json-schemas/fabric/gitIntegration/"
        r"platformProperties/2\.\d+\.\d+/schema\.json$",
    f"{NAME}.SemanticModel/definition.pbism":
        r"^https://developer\.microsoft\.com/json-schemas/fabric/item/semanticModel/"
        r"definitionProperties/1\.\d+\.\d+/schema\.json$",
    f"{NAME}.Report/.platform":
        r"^https://developer\.microsoft\.com/json-schemas/fabric/gitIntegration/"
        r"platformProperties/2\.\d+\.\d+/schema\.json$",
    f"{NAME}.Report/definition.pbir":
        r"^https://developer\.microsoft\.com/json-schemas/fabric/item/report/"
        r"definitionProperties/2\.\d+\.\d+/schema\.json$",
    f"{NAME}.Report/definition/report.json":
        r"^https://developer\.microsoft\.com/json-schemas/fabric/item/report/"
        r"definition/report/3\.\d+\.\d+/schema\.json$",
    f"{NAME}.Report/definition/pages/pages.json":
        r"^https://developer\.microsoft\.com/json-schemas/fabric/item/report/"
        r"definition/pagesMetadata/1\.\d+\.\d+/schema\.json$",
}
PAGE_SCHEMA_RE = (r"^https://developer\.microsoft\.com/json-schemas/fabric/item/report/"
                  r"definition/page/2\.\d+\.\d+/schema\.json$")
VIS_SCHEMA_RE = (r"^https://developer\.microsoft\.com/json-schemas/fabric/item/report/"
                 r"definition/visualContainer/2\.\d+\.\d+/schema\.json$")

for rel, pattern in SCHEMA_RULES.items():
    checks += 1
    fp = os.path.join(BASE, rel)
    if not os.path.exists(fp):
        continue
    got = json.load(open(fp, encoding="utf-8")).get("$schema", "")
    if not re.match(pattern, got):
        fail(f"{rel}: $schema is '{got}', which Desktop will reject")

if os.path.isdir(pages_dir):
    for pg in sorted(page_keys_on_disk):
        pj2 = os.path.join(pages_dir, pg, "page.json")
        if os.path.exists(pj2):
            checks += 1
            got = json.load(open(pj2, encoding="utf-8")).get("$schema", "")
            if not re.match(PAGE_SCHEMA_RE, got):
                fail(f"{pg}/page.json: $schema is '{got}'")
        vdir2 = os.path.join(pages_dir, pg, "visuals")
        if os.path.isdir(vdir2):
            for vs in sorted(os.listdir(vdir2)):
                vf2 = os.path.join(vdir2, vs, "visual.json")
                if os.path.exists(vf2):
                    checks += 1
                    got = json.load(open(vf2, encoding="utf-8")).get("$schema", "")
                    if not re.match(VIS_SCHEMA_RE, got):
                        fail(f"{pg}/{vs}/visual.json: $schema is '{got}'")


# ---------------------------------------------------------------------------
# 8 · model.tmdl references every table file
# ---------------------------------------------------------------------------
mp = os.path.join(SM, "model.tmdl")
if os.path.exists(mp):
    mtext = open(mp, encoding="utf-8").read()
    refd = set(re.findall(r"^ref table\s+(\S+)$", mtext, re.M))
    for t in sorted(set(model) - refd):
        fail(f"model.tmdl has no 'ref table {t}' — the table will not load")
    for t in sorted(refd - set(model)):
        fail(f"model.tmdl references table '{t}' with no .tmdl file")
    checks += len(refd)


# ---------------------------------------------------------------------------
# 9 · Every CSV the M layer reads exists in the shipped data folder
# ---------------------------------------------------------------------------
needed = set()
for fn in tmdl_files:
    if fn.endswith(".tmdl"):
        text = open(os.path.join(tables_dir, fn), encoding="utf-8").read()
        needed |= set(re.findall(r'fnSource\("([^"]+)"\)', text))
data_dir = os.path.join(BASE, "data")
if os.path.isdir(data_dir):
    have = {f[:-4] for f in os.listdir(data_dir) if f.endswith(".csv")}
    for miss in sorted(needed - have):
        fail(f"powerbi/data/{miss}.csv missing — Local source mode will fail")
    checks += len(needed)
else:
    warn("powerbi/data/ not present — set LocalDataFolder to wherever the CSVs are")


# ---------------------------------------------------------------------------
# 10 · Every column the M layer types exists in the CSV it reads, and every
#      column declared in TMDL is produced by the query
# ---------------------------------------------------------------------------
import csv as _csv

n_col = 0
for fn in tmdl_files:
    if not fn.endswith(".tmdl") or fn == "_Measures.tmdl":
        continue
    text = open(os.path.join(tables_dir, fn), encoding="utf-8").read()
    tname = re.search(r"^table\s+(\S+)", text, re.M).group(1).strip("'")
    src = re.search(r'fnSource\("([^"]+)"\)', text)
    if not src:
        continue                              # Dim_Date is generated in M
    csv_path = os.path.join(BASE, "data", src.group(1) + ".csv")
    if not os.path.exists(csv_path):
        continue                              # already reported by check 9
    with open(csv_path, encoding="utf-8") as fh:
        header = set(next(_csv.reader(fh)))

    typed = set(re.findall(r'\{"([^"]+)",\s*(?:type\s+\w+|Int64\.Type)\}', text))
    for c in sorted(typed - header):
        n_col += 1
        fail(f"{tname}: M types column '{c}' that {src.group(1)}.csv does not have")

    # every TMDL column must be produced by the query: either straight from the
    # CSV, or added by an explicit Table.AddColumn step
    added = set(re.findall(r'Table\.AddColumn\([^,]+,\s*"([^"]+)"', text))
    for c in sorted(model.get(tname, set()) - header - added):
        n_col += 1
        fail(f"{tname}: TMDL declares column '{c}' that the query never produces")

    # a column in the CSV that the model ignores is fine, but worth knowing
    unmapped = header - model.get(tname, set())
    if unmapped:
        warn(f"{tname}: CSV columns not surfaced in the model: "
             f"{', '.join(sorted(unmapped))}")
checks += n_col if n_col else len(tmdl_files)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
print()
print(f"  project        {BASE}")
print(f"  tables         {len(model)}  ({len(partitions)} with partitions)")
print(f"  measures       {len(measures)}")
print(f"  relationships  {n_rel // 2}")
print(f"  pages          {len(page_keys_on_disk)}")
print(f"  visuals        {n_vis}")
print(f"  field refs     {n_refs} checked against the model")
print(f"  dax refs       {n_dax} checked against the model")
print(f"  json files     {len(json_files)} parsed")
print(f"  $schema urls   checked against the patterns Desktop enforces")
print(f"  m/csv columns  cross-checked for every imported table")
print(f"  ---- {checks} checks ----")
print()

for wmsg in warnings:
    print(f"  WARN   {wmsg}")
if errors:
    for e in errors:
        print(f"  ERROR  {e}")
    print(f"\n  {len(errors)} problem(s). Fix before opening in Power BI Desktop.\n")
    sys.exit(1)

print("  PASS - the project is internally consistent.\n")
