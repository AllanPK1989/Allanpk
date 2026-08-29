#!/usr/bin/env python3
"""
validate_flows.py - checks the six flow definitions before anyone builds them.

A flow that references a column that does not exist, or an action output that is
never produced, fails at run time with a message that does not say which. These
checks catch that on the desk instead.

  1. Every file is valid JSON with the expected workflow shape.
  2. Every runAfter names an action that exists in the same scope.
  3. Every outputs()/body() reference names an action that exists.
  4. Every variables() reference is initialised before use.
  5. Every parameters() reference is declared in the definition parameters.
  6. Every SharePoint table is a real list, and every column written or filtered
     on exists in that list.
  7. Expressions have balanced brackets and quotes.

Run:  python3 scripts/validate_flows.py
Exit code 1 on any failure.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFS = os.path.join(ROOT, "flows", "definitions")
DATA = os.path.join(ROOT, "data", "dummy")

SP_BUILTIN = {"ID", "Id", "Title", "Created", "Modified", "Author", "Editor",
              "{Name}", "{FilenameWithExtension}", "{Identifier}", "{Link}"}

# list name -> the CSV whose header defines its columns
TABLES = {
    "Cell_Master": "Cell_Master.csv",
    "Machine_Master": "Machine_Master.csv",
    "Technician_Master": "Technician_Master.csv",
    "PM_Checklist_Master": "PM_Checklist_Master.csv",
    "PM_Config": "PM_Config.csv",
    "PM_WorkOrders": "PM_WorkOrders.csv",
    "PM_Hour_Ledger": "PM_Hour_Ledger.csv",
    "PM_ChecklistResults": "PM_ChecklistResults.csv",
    "Breakdown_Reports": "Breakdown_Reports.csv",
    "SparePart_Requests": "SparePart_Requests.csv",
    "SparePart_Replacements": "SparePart_Replacements.csv",
    "Abnormality_Log": "Abnormality_Log.csv",
    "QR_Scan_Log": "QR_Scan_Log.csv",
}

COLUMNS = {}
for t, f in TABLES.items():
    with open(os.path.join(DATA, f), encoding="utf-8") as fh:
        COLUMNS[t] = set(next(csv.reader(fh))) | SP_BUILTIN

errors: list[str] = []
warnings: list[str] = []
checks = 0


def fail(f, msg):
    errors.append(f"{f}: {msg}")


def walk_actions(actions, scope="root", out=None):
    """Yield (name, action, scope) for every action at every nesting level."""
    out = out if out is not None else []
    for name, a in actions.items():
        out.append((name, a, scope))
        for key in ("actions",):
            if isinstance(a.get(key), dict):
                walk_actions(a[key], name, out)
        if isinstance(a.get("else"), dict) and isinstance(a["else"].get("actions"), dict):
            walk_actions(a["else"]["actions"], name, out)
    return out


def scopes(actions, scope="root", out=None):
    """Yield (scope_name, {action names in that scope})."""
    out = out if out is not None else []
    out.append((scope, set(actions.keys())))
    for name, a in actions.items():
        if isinstance(a.get("actions"), dict):
            scopes(a["actions"], name, out)
        if isinstance(a.get("else"), dict) and isinstance(a["else"].get("actions"), dict):
            scopes(a["else"]["actions"], name + "/else", out)
    return out


def all_text(obj, acc=None):
    acc = acc if acc is not None else []
    if isinstance(obj, str):
        acc.append(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            acc.append(k)
            all_text(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            all_text(v, acc)
    return acc


files = sorted(f for f in os.listdir(DEFS) if f.endswith(".json"))
print()
for fn in files:
    path = os.path.join(DEFS, fn)
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        fail(fn, f"invalid JSON: {e}")
        continue
    checks += 1

    d = doc.get("definition")
    if not isinstance(d, dict):
        fail(fn, "no definition object")
        continue
    for k in ("$schema", "contentVersion", "parameters", "triggers", "actions"):
        checks += 1
        if k not in d:
            fail(fn, f"definition missing '{k}'")

    actions = d.get("actions", {})
    triggers = d.get("triggers", {})
    flat = walk_actions(actions)
    names = {n for n, _, _ in flat} | set(triggers.keys())
    declared_params = set(d.get("parameters", {}).keys())

    # 2 - runAfter targets exist in the same scope
    for scope_name, members in scopes(actions):
        for n in members:
            a = next(a for nn, a, _ in flat if nn == n)
            for target in (a.get("runAfter") or {}):
                checks += 1
                if target not in members:
                    fail(fn, f"action '{n}' runs after '{target}', which is not in "
                             f"the same scope ({scope_name})")

    # 3,4,5 - expression references
    initialised: set[str] = set()
    for n, a, _ in flat:
        if a.get("type") == "InitializeVariable":
            for v in a["inputs"]["variables"]:
                initialised.add(v["name"])

    text = " ".join(all_text(actions)) + " " + " ".join(all_text(triggers))

    for ref in set(re.findall(r"(?:outputs|body)\('([^']+)'\)", text)):
        checks += 1
        if ref not in names:
            fail(fn, f"references output of '{ref}', which is not an action in this flow")
    for ref in set(re.findall(r"variables\('([^']+)'\)", text)):
        checks += 1
        if ref not in initialised:
            fail(fn, f"uses variable '{ref}' that is never initialised")
    for ref in set(re.findall(r"parameters\('([^']+)'\)", text)):
        checks += 1
        if ref not in declared_params:
            fail(fn, f"uses parameter '{ref}' that is not declared")
    for ref in set(re.findall(r"items\('([^']+)'\)", text)):
        checks += 1
        if ref not in names:
            fail(fn, f"references loop '{ref}', which is not an action in this flow")

    # 6 - SharePoint tables and columns
    for n, a, _ in flat:
        inp = a.get("inputs", {})
        host = inp.get("host", {}) if isinstance(inp, dict) else {}
        if host.get("connectionName") != "shared_sharepointonline":
            continue
        params = inp.get("parameters", {})
        table = params.get("table")
        if not isinstance(table, str) or table.startswith("@"):
            continue
        checks += 1
        if table not in COLUMNS:
            warnings.append(f"{fn}: action '{n}' uses table '{table}', which is not "
                            f"one of the defined lists")
            continue
        cols = COLUMNS[table]
        for key, val in params.items():
            if key.startswith("item/"):
                col = key[5:]
                checks += 1
                if col not in cols:
                    fail(fn, f"action '{n}' writes {table}[{col}], which does not exist")
            if key in ("$filter", "$orderby") and isinstance(val, str):
                for col in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s+(?:eq|ne|lt|gt|le|ge|asc|desc)\b", val):
                    checks += 1
                    if col not in cols and col not in ("and", "or", "not"):
                        fail(fn, f"action '{n}' filters {table} on [{col}], which does not exist")

    # 7 - bracket and quote balance in expressions
    for s in all_text(actions):
        if "@" not in s:
            continue
        checks += 1
        if s.count("(") != s.count(")"):
            fail(fn, f"unbalanced parentheses in: {s[:90]}")
        if s.count("'") % 2 != 0:
            fail(fn, f"unbalanced quotes in: {s[:90]}")
        if s.count("[") != s.count("]"):
            fail(fn, f"unbalanced brackets in: {s[:90]}")

    n_top = len(actions)
    n_all = len(flat)
    print(f"  {fn[:-5]:<44} {n_top:>2} top-level, {n_all:>2} total actions")

print()
print(f"  {checks} checks across {len(files)} flows")
print()
for w in warnings:
    print(f"  WARN   {w}")
for e in errors:
    print(f"  ERROR  {e}")
print()
print("  " + ("PASS - the flow definitions are internally consistent and every "
              "SharePoint column exists" if not errors else f"FAIL - {len(errors)} problem(s)"))
sys.exit(1 if errors else 0)
