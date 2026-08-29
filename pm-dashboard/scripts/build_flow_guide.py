#!/usr/bin/env python3
"""
build_flow_guide.py - turns the six flow definitions into a click-by-click build
guide, generated from the JSON so the two can never disagree.
"""
from __future__ import annotations
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFS = os.path.join(ROOT, "flows", "definitions")

ACTION_LABEL = {
    "OpenApiConnection": "connector action",
    "Compose": "Compose",
    "InitializeVariable": "Initialize variable",
    "SetVariable": "Set variable",
    "IncrementVariable": "Increment variable",
    "If": "Condition",
    "Foreach": "Apply to each",
    "Query": "Filter array",
    "Select": "Select",
    "Terminate": "Terminate",
    "Response": "Respond to a PowerApp or flow",
    "Workflow": "Run a child flow",
    "Recurrence": "Recurrence",
    "Request": "Manually trigger / PowerApps",
}
OP_LABEL = {
    "GetItems": "Get items", "PostItem": "Create item", "PatchItem": "Update item",
    "GetItem": "Get item", "OnNewItems": "When an item is created",
    "OnNewFileV2": "When a file is created (properties only)",
    "GetFileItems": "Get files (properties only)",
    "SendEmailV2": "Send an email (V2)",
    "PostMessageToConversation": "Post message in a chat or channel",
    "StartAndWaitForAnApproval": "Start and wait for an approval",
}


def describe(name, a, depth=0):
    pad = "  " * depth
    t = a.get("type", "")
    inp = a.get("inputs", {})
    host = inp.get("host", {}) if isinstance(inp, dict) else {}
    if t == "OpenApiConnection":
        op = host.get("operationId", "")
        conn = host.get("connectionName", "").replace("shared_", "")
        label = f"**{OP_LABEL.get(op, op)}** ({conn})"
    else:
        label = f"**{ACTION_LABEL.get(t, t)}**"
    lines = [f"{pad}- `{name}` — {label}"]
    if a.get("description"):
        lines.append(f"{pad}  <br>*{a['description']}*")

    if t == "OpenApiConnection":
        for k, v in (inp.get("parameters") or {}).items():
            if k in ("dataset", "authentication"):
                continue
            lines.append(f"{pad}  - `{k}`: `{v}`")
    elif t in ("Compose",):
        lines.append(f"{pad}  - Inputs: `{inp}`")
    elif t == "InitializeVariable":
        for v in inp["variables"]:
            lines.append(f"{pad}  - `{v['name']}` ({v['type']}) = `{v['value']}`")
    elif t in ("SetVariable", "IncrementVariable"):
        lines.append(f"{pad}  - `{inp['name']}` = `{inp['value']}`")
    elif t == "Query":
        lines.append(f"{pad}  - From: `{inp['from']}`")
        lines.append(f"{pad}  - Where: `{inp['where']}`")
    elif t == "Select":
        lines.append(f"{pad}  - From: `{inp['from']}` → `{inp['select']}`")
    elif t == "Terminate":
        lines.append(f"{pad}  - Status: `{inp['runStatus']}`"
                     + (f", message: *{inp['runError']['message']}*" if inp.get("runError") else ""))
    elif t == "If":
        lines.append(f"{pad}  - Condition: `{json.dumps(a['expression'])}`")
    elif t == "Foreach":
        lines.append(f"{pad}  - Over: `{a['foreach']}`")
        c = a.get("runtimeConfiguration", {}).get("concurrency", {}).get("repetitions")
        if c is not None:
            lines.append(f"{pad}  - **Concurrency must be set to {c}** (Settings ▸ Concurrency Control)")
    elif t == "Workflow":
        lines.append(f"{pad}  - Child flow: `{inp['host']['workflowReferenceName']}`")
        for k, v in inp.get("body", {}).items():
            lines.append(f"{pad}  - `{k}`: `{v}`")

    for key, sub in (("actions", "then"), ("else", "else")):
        block = a.get(key)
        if key == "else" and isinstance(block, dict):
            block = block.get("actions")
        if isinstance(block, dict) and block:
            lines.append(f"{pad}  - *{sub}:*")
            for n2, a2 in block.items():
                lines += describe(n2, a2, depth + 2)
    return lines


out = ["# Power Automate — Build Guide",
       "",
       "Six flows. Flow 2 owns the scheduling rule; the other five keep the system honest.",
       "",
       "> Generated from `flows/definitions/*.json` by `scripts/build_flow_guide.py`, so "
       "the guide and the definitions cannot drift. `scripts/validate_flows.py` checks both.",
       "",
       "## Before you start",
       "",
       "1. Create the flows in a **solution**, not in *My flows*. Solutions are what make "
       "the flows movable between environments later; retrofitting that is painful.",
       "2. Add connection references for **SharePoint**, **Office 365 Outlook**, "
       "**Microsoft Teams**, **Excel Online (Business)** and **Approvals**.",
       "3. Every flow reads the site URL from an environment variable rather than a "
       "hard-coded string. Create `SharePointSiteUrl` first.",
       "4. Turn on failure notifications on all six (⋯ ▸ Settings ▸ Notify on failure). "
       "A flow that fails silently is worse than no flow.",
       "",
       "## Reading this guide",
       "",
       "Each action is listed with the name to give it. **Names matter** — the expressions "
       "reference other actions by name, so a renamed action breaks everything downstream. "
       "Indented bullets are actions nested inside a condition or a loop.",
       "",
       "---",
       ""]

for fn in sorted(os.listdir(DEFS)):
    if not fn.endswith(".json"):
        continue
    doc = json.load(open(os.path.join(DEFS, fn), encoding="utf-8"))
    d = doc["definition"]
    num = fn.split("_")[1]
    out += [f"## Flow {num} — {doc['_name']}", ""]
    for n in doc.get("_notes", []):
        out.append(f"> {n}")
        out.append(">")
    out += ["", "### Trigger", ""]
    for n, a in d["triggers"].items():
        out += describe(n, a)
    out += ["", "### Actions", ""]
    for n, a in d["actions"].items():
        out += describe(n, a)
    params = d.get("parameters", {})
    custom = {k: v for k, v in params.items() if not k.startswith("$")}
    if custom:
        out += ["", "### Environment variables this flow needs", "",
                "| Name | Default | What it is |", "|------|---------|------------|"]
        DESC = {
            "SharePointSiteUrl": "Root URL of the PMSystem site",
            "StdHoursFolderId": "Folder the monthly upload lands in",
            "DocumentLibraryDriveId": "Drive id of Shared Documents, for the Excel action",
            "UploaderEmail": "Who to chase when an upload is missing or wrong",
            "SchedulerFlowId": "The child flow id of Flow 2",
            "MaintenanceHeadEmail": "Approver below the spare limit; abnormality escalation",
            "PlantHeadEmail": "Approver above the spare limit",
            "TeamsGroupId": "Team the digest is posted to",
            "TeamsChannelId": "Channel the digest is posted to",
            "StdHoursLibraryId": "Library holding the monthly uploads",
        }
        for k, v in custom.items():
            out.append(f"| `{k}` | `{v.get('defaultValue','')}` | {DESC.get(k,'')} |")
    out += ["", "---", ""]

out += ["## After you build them", "",
        "1. Run **Flow 2** by hand with `Mode = Backload`, once per historical month, "
        "oldest first, using the history back-load workbook. Skip work order creation for "
        "those months — historical PMs were done on paper.",
        "2. Reconcile: does the ledger's last-PM date per cell match the maintenance "
        "register? Fix that before going further, because every carry-over depends on it.",
        "3. Upload one real monthly file and watch Flow 1 → Flow 2 run end to end.",
        "4. Check the work orders that appear against what you expected. If a cell you "
        "expected did not trip, look at its ledger row: opening, added, closing, threshold. "
        "The row tells you which of the four is wrong.",
        ""]

path = os.path.join(ROOT, "flows", "BUILD_GUIDE.md")
open(path, "w", encoding="utf-8").write("\n".join(out))
print(f"  flows/BUILD_GUIDE.md  ({len(out)} lines)")
