#!/usr/bin/env python3
"""Generates docs/08-dax-measure-library.md from pbi_measures.py, so the
documentation can never drift from the model."""

import os
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pbi_measures import MEASURES  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

groups = OrderedDict()
for name, folder, fmt, dax, desc in MEASURES:
    groups.setdefault(folder, []).append((name, fmt, dax.strip(), desc))

out = ["# 08 · DAX Measure Library",
       "",
       f"{len(MEASURES)} measures, all on the `_Measures` table, organised into "
       f"{len(groups)} display folders.",
       "",
       "> Generated from `scripts/pbi_measures.py` by `scripts/build_measure_docs.py`. "
       "Edit the Python file, not this one, then re-run both that script and "
       "`scripts/build_pbip.py`.",
       "",
       "## Contents", ""]

for folder in groups:
    anchor = folder.lower().replace(" ", "-")
    out.append(f"- [{folder}](#{anchor}) — {len(groups[folder])} measures")
out.append("")

for folder, items in groups.items():
    out.append(f"## {folder}")
    out.append("")
    out.append("| Measure | Format | What it means |")
    out.append("|---------|--------|---------------|")
    for name, fmt, dax, desc in items:
        out.append(f"| `{name}` | `{fmt or 'text'}` | {desc} |")
    out.append("")
    for name, fmt, dax, desc in items:
        out.append(f"### {name}")
        out.append("")
        out.append(desc)
        out.append("")
        out.append("```dax")
        out.append(f"{name} =")
        out.append(dax)
        out.append("```")
        out.append("")

with open(os.path.join(ROOT, "docs", "08-dax-measure-library.md"), "w",
          encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")

print(f"docs/08-dax-measure-library.md written ({len(MEASURES)} measures)")
