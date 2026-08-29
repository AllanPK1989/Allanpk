#!/usr/bin/env python3
"""
compare_to_reference.py - diffs the generated project's file layout against a
real Power BI project published by Microsoft.

Four rounds of "Desktop will not open it" were four separate missing or wrong
files, each found one at a time from one error message. This finds all of them
at once. Run it whenever the project structure changes.

Get the reference (a sparse clone, so it is quick):

    git clone --depth 1 --filter=blob:none --sparse \\
        https://github.com/microsoft/bcapps /tmp/bcapps
    cd /tmp/bcapps && git sparse-checkout set \\
        "src/Apps/W1/PowerBIReports/Power BI Files/Sales app"

    python3 scripts/compare_to_reference.py \\
        "/tmp/bcapps/src/Apps/W1/PowerBIReports/Power BI Files/Sales app"

Exits 0 and skips if the reference is not present.
"""
from __future__ import annotations
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "powerbi")

# Present in the reference but not required. Verified by counting: mobile.json
# appears on 32 of 179 visuals and on no visual at all on some pages, so it is
# written only for visuals that have been placed in a mobile layout.
OPTIONAL = {
    "<MODEL>/definition/cultures/*.tmdl":  "localisation, only if you translate the model",
    "<MODEL>/.pbi/editorSettings.json":    "Desktop UI state",
    "<MODEL>/DAXQueries/*":                "saved DAX queries",
    "<MODEL>/diagramLayout.json":          "model diagram positions",
    "<REPORT>/StaticResources/*":          "only if report.json references a resource",
    "<REPORT>/definition/pages/*/visuals/*/mobile.json":
                                           "only for visuals placed in a mobile layout",
}


def shape(root: str, proj: str) -> set[str]:
    out = set()
    for r, _d, fs in os.walk(root):
        for f in fs:
            rel = os.path.relpath(os.path.join(r, f), root).replace("\\", "/")
            rel = (rel.replace(proj + ".Report", "<REPORT>")
                      .replace(proj + ".SemanticModel", "<MODEL>")
                      .replace(proj + ".pbip", "<PROJECT>.pbip"))
            rel = re.sub(r"<REPORT>/definition/pages/[^/]+/visuals/[^/]+/",
                         "<REPORT>/definition/pages/*/visuals/*/", rel)
            rel = re.sub(r"<REPORT>/definition/pages/[^/]+/page\.json",
                         "<REPORT>/definition/pages/*/page.json", rel)
            rel = re.sub(r"<MODEL>/definition/tables/.*", "<MODEL>/definition/tables/*.tmdl", rel)
            rel = re.sub(r"<MODEL>/definition/cultures/.*", "<MODEL>/definition/cultures/*.tmdl", rel)
            rel = re.sub(r"<REPORT>/StaticResources/.*", "<REPORT>/StaticResources/*", rel)
            rel = re.sub(r"<MODEL>/DAXQueries/.*", "<MODEL>/DAXQueries/*", rel)
            out.add(rel)
    return out


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ref_dir = sys.argv[1]
    if not os.path.isdir(ref_dir):
        print(f"\n  reference not found at {ref_dir} - skipping\n")
        return
    proj = next((d[:-7] for d in os.listdir(ref_dir) if d.endswith(".Report")), None)
    if not proj:
        sys.exit(f"  {ref_dir} does not look like a PBIP project")

    ref, mine = shape(ref_dir, proj), shape(MINE, "PM_Dashboard")
    missing = sorted(ref - mine)
    required = [m for m in missing if m not in OPTIONAL]

    print(f"\n  reference : {proj}")
    print(f"  ours      : PM_Dashboard\n")
    for m in missing:
        note = OPTIONAL.get(m)
        print(f"    {'optional' if note else 'REQUIRED'}  {m}" + (f"   ({note})" if note else ""))
    if not missing:
        print("    nothing missing")
    print()
    print("  " + ("PASS - every required file the reference has is present"
                 if not required else f"FAIL - missing: {', '.join(required)}"))
    sys.exit(1 if required else 0)


if __name__ == "__main__":
    main()
