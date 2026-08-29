#!/usr/bin/env python3
"""
build_model_guide.py - generates the step-by-step guide for building the semantic
model by hand in Power BI Desktop: parameters, functions, 17 queries, column
types, 28 relationships and where the 94 measures go.

Generated from the same specs that produce the TMDL, so the hand-build route and
the generated project cannot describe different models.

Run:  python3 scripts/build_model_guide.py
Out:  docs/12-model-build-guide.md
"""
from __future__ import annotations
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build_pbip as B                                   # noqa: E402
from pbi_model_spec import RELATIONSHIPS, TABLES         # noqa: E402
from pbi_measures import MEASURES                        # noqa: E402

B.emit_expressions()          # populates B.EXPRESSION_SPECS

DTYPE_UI = {"string": "Text", "int64": "Whole number",
            "double": "Decimal number", "dateTime": "Date"}

out = ["# 12 · Model Build Guide",
       "",
       "Building the semantic model by hand in Power BI Desktop. Nothing here depends "
       "on a file format matching your Desktop version.",
       "",
       "> Generated from the same table, relationship and measure definitions that "
       "produce the project files.",
       "",
       f"**What you are building:** {len(TABLES)} tables + a measures table, "
       f"{len(RELATIONSHIPS)} relationships, {len(MEASURES)} measures.",
       "",
       "**Time:** about half a day. The measures are the long part; paste them in "
       "folder order and it goes quickly.",
       "",
       "---", "",
       "## Step 1 · New file and preview features", "",
       "1. Power BI Desktop ▸ **Blank report**.",
       "2. **File ▸ Options and settings ▸ Options ▸ Preview features**. Nothing here "
       "is required if you save as `.pbix`; tick **Store semantic model using TMDL "
       "format** and **Enhanced report format (PBIR)** only if you intend to save as "
       "a `.pbip` project.",
       "3. **File ▸ Options ▸ Current file ▸ Regional settings**: set the locale you "
       "report in. The queries below parse dates as `en-US` explicitly, so this does "
       "not change how data loads.",
       "",
       "---", "",
       "## Step 2 · Parameters and functions", "",
       "**Home ▸ Transform data** to open Power Query. Then **Home ▸ Manage "
       "parameters ▸ New parameter** for each parameter below, and **Home ▸ New "
       "source ▸ Blank query** for each function (then **Home ▸ Advanced editor** and "
       "paste the body).",
       "",
       "Name each one exactly as shown — every table query calls `fnSource` by name.",
       ""]

for name, kind, body, desc in B.EXPRESSION_SPECS:
    out += [f"### `{name}` — {kind}", "", desc, ""]
    if kind == "parameter":
        out += [f"Type **Text**. Current value: `{body}`", ""]
    else:
        out += ["```m", body.strip(), "```", ""]

out += ["> Put the three parameters in a query group called **Parameters** and the "
        "five functions in one called **Functions** (right-click ▸ Move to group). "
        "It keeps the query list readable once there are 25 entries.",
        "",
        "---", "",
        "## Step 3 · The 17 table queries", "",
        "For each one: **Home ▸ New source ▸ Blank query**, then **Advanced editor**, "
        "paste, and rename the query to the heading exactly. The name matters — every "
        "measure and every visual references it.",
        "",
        "Set **Home ▸ Close & apply** only after all 17 are in.",
        ""]

for spec in TABLES:
    name = spec["name"]
    cols = B.table_columns(spec)
    out += [f"### `{name}`", ""]
    if spec.get("desc"):
        out += [spec["desc"], ""]
    out += ["```m", B.build_table_m(spec).strip(), "```", "",
            f"{len(cols)} columns. Types are set by the query itself, so there is "
            "nothing to change in the ribbon.", ""]
    if spec.get("date_table"):
        out += ["**Mark as a date table.** After loading: right-click `Dim_Date` in the "
                "Data pane ▸ **Mark as date table** ▸ choose the `Date` column. Time "
                "intelligence will not work without this.", ""]
    if spec.get("hidden"):
        out += [f"**Hide it.** Right-click `{name}` in the Data pane ▸ **Hide**. It is "
                "read by measures, not by people.", ""]
    non_default = [(c, t) for c, t in cols if t in ("int64", "double")]
    if non_default:
        out += ["Set **Summarization: Don't summarize** on these numeric columns so "
                "nobody drags a raw sum into a visual by accident — the measures do the "
                "aggregating:", "",
                ", ".join(f"`{c}`" for c, _t in non_default), ""]
    out += ["---", ""]

out += ["## Step 4 · Relationships", "",
        "**Model view ▸ Manage relationships ▸ New**. Create all "
        f"{len(RELATIONSHIPS)} exactly as listed. Cardinality is **Many to one (\\*:1)** "
        "and cross-filter direction is **Single** on every one of them.",
        "",
        "Drag from the *From* column to the *To* column — the direction matters.",
        "",
        "| # | From (many) | To (one) | Active |",
        "|---|-------------|----------|--------|"]
for i, (ft, fc, tt, tc, active) in enumerate(RELATIONSHIPS, start=1):
    out.append(f"| {i} | `{ft}[{fc}]` | `{tt}[{tc}]` | "
               f"{'Yes' if active else '**No** — untick Active'} |")
out += ["",
        "The three inactive ones are alternate date roles on the work order table. They "
        "exist so a measure can use `USERELATIONSHIP` to analyse by completion date or "
        "due date without needing a second date table. Power BI will refuse to make "
        "them active — that is correct, leave them unticked.",
        "",
        "> If a relationship will not create, the usual cause is the *To* column not "
        "being unique. Check for blank rows in the dimension — a single blank key will "
        "block it.",
        "",
        "---", "",
        "## Step 5 · The measures table", "",
        "1. **Home ▸ Enter data**. Leave the single column and row as they are, name "
        "the table `_Measures`, **Load**.",
        "2. In the Data pane, expand `_Measures`, right-click the `Column1` column ▸ "
        "**Hide**.",
        "3. Create every measure from `08-dax-measure-library.md`. For each one: "
        "select `_Measures` ▸ **Modeling ▸ New measure** ▸ paste the DAX.",
        "4. Set its **Format** and its **Display folder** from the same document.",
        "",
        f"There are {len(MEASURES)} measures in "
        f"{len({m[1] for m in MEASURES})} folders. Work through one folder at a time — "
        "later folders reference measures from earlier ones, so in order they will all "
        "resolve as you go.",
        "",
        "| Folder | Measures |",
        "|--------|---------:|"]
folders: dict[str, int] = {}
for m in MEASURES:
    folders[m[1]] = folders.get(m[1], 0) + 1
for f, n in sorted(folders.items()):
    out.append(f"| {f} | {n} |")
out += ["",
        "> Measure names contain spaces and `%` signs. Type them exactly — the report "
        "build guide references them by name.",
        "",
        "---", "",
        "## Step 6 · Check the model before building visuals", "",
        "In **Model view**, confirm:",
        "",
        f"- {len(TABLES) + 1} tables, `Config` and `_Measures` hidden",
        f"- {len(RELATIONSHIPS)} relationships, {sum(1 for r in RELATIONSHIPS if not r[4])} "
        "of them inactive (dashed lines)",
        "- `Dim_Date` marked as a date table",
        "- No relationship between `Fact_ChecklistResults` and `Dim_Machine` or "
        "`Dim_Date` directly — it hangs off `Fact_WorkOrders`, and adding those would "
        "create ambiguous filter paths that Power BI will reject",
        "",
        "Then drop a card on a page with `[PM Compliance %]` and one with "
        "`[Std Hours]`. If both show a number, the model works and you can move on to "
        "`13-report-build-guide.md`.",
        ""]

path = os.path.join(ROOT, "docs", "12-model-build-guide.md")
open(path, "w", encoding="utf-8").write("\n".join(out))
print(f"  docs/12-model-build-guide.md  ({len(TABLES)} tables, "
      f"{len(RELATIONSHIPS)} relationships, {len(MEASURES)} measures, {len(out)} lines)")
