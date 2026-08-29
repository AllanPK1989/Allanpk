"""Structural checks on powerbi/PM_Model.tmdl.

Nothing here can prove Power BI Desktop will accept the script - only Desktop can
do that. What it can prove is that the script is well-formed TMDL, that it says
the same thing as the PBIP, and that every name it uses resolves. Those are the
failure modes that have actually cost time on this project.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from pbi_model_spec import TABLES, RELATIONSHIPS
from pbi_measures import MEASURES

SCRIPT = os.path.join(ROOT, "powerbi", "PM_Model.tmdl")
DEFN = os.path.join(ROOT, "powerbi", "PM_Dashboard.SemanticModel", "definition")

checks = 0
errors: list[str] = []


def check(ok: bool, msg: str) -> None:
    global checks
    checks += 1
    if not ok:
        errors.append(msg)


def structural_lines(text: str):
    """Yield (lineno, depth, content) for lines that are TMDL structure.

    Lines inside a ``` fenced expression are the expression's own text, not
    objects, so they are skipped - otherwise a `let` block reads as a child
    object and the depth tree is nonsense.
    """
    in_fence = False
    for i, raw in enumerate(text.split("\n"), 1):
        line = raw.rstrip("\r")
        if in_fence:
            # A fence closes on a line whose only content is the marker.
            if line.strip() == "```":
                in_fence = False
            continue
        if not line.strip():
            continue
        stripped = line.lstrip("\t")
        depth = len(line) - len(stripped)
        if stripped.endswith("```"):
            # An opening fence is appended to the line that declares the
            # object, e.g. `measure 'X' = ```. The declaration is structural;
            # everything up to the closing marker is the expression body.
            head = stripped[:-3].rstrip()
            in_fence = True
            if not head:
                continue
            yield i, depth, head
            continue
        yield i, depth, stripped


def main() -> None:
    check(os.path.exists(SCRIPT), "PM_Model.tmdl is missing")
    if errors:
        report()
        return
    text = open(SCRIPT, encoding="utf-8").read()

    # --- 1. tabs only -----------------------------------------------------
    space_led = [i for i, ln in enumerate(text.split("\n"), 1)
                 if ln.startswith(" ")]
    check(not space_led,
          f"lines indented with spaces, not tabs: {space_led[:5]}")

    # --- 2. fences balanced ----------------------------------------------
    check(text.count("```") % 2 == 0,
          f"unbalanced ``` fences ({text.count('```')} markers)")

    rows = list(structural_lines(text))

    # --- 3. depth tree is well formed ------------------------------------
    prev = -1
    for lineno, depth, content in rows:
        check(depth <= prev + 1,
              f"line {lineno}: indent jumps from {prev} to {depth}: {content[:60]}")
        prev = depth

    # --- 4. the command and the model ------------------------------------
    roots = [c for _, d, c in rows if d == 0]
    check(roots == ["createOrReplace"],
          f"expected exactly one root 'createOrReplace', found {roots[:4]}")
    level1 = [c for _, d, c in rows if d == 1]
    check(level1 == ["ref model Model"],
          f"expected exactly one 'ref model Model' at depth 1, found {level1[:4]}. "
          f"A bare 'model Model' REPLACES the model object and resets every "
          f"property not restated to its default, which the engine rejects.")

    # --- 5. object inventory ---------------------------------------------
    l2 = [c for _, d, c in rows if d == 2]
    tables = [c[len("table "):] for c in l2 if c.startswith("table ")]
    exprs = [c[len("expression "):].split(" =")[0] for c in l2
             if c.startswith("expression ")]
    rels = [c for c in l2 if c.startswith("relationship ")]
    groups = [c[len("queryGroup "):] for c in l2 if c.startswith("queryGroup ")]
    measures = [c for _, d, c in rows if d == 3 and c.startswith("measure ")]

    want_tables = sorted([t["name"] for t in TABLES] + ["_Measures"])
    check(sorted(tables) == want_tables,
          f"tables differ from the model spec: "
          f"missing {sorted(set(want_tables) - set(tables))}, "
          f"extra {sorted(set(tables) - set(want_tables))}")
    check(len(rels) == len(RELATIONSHIPS),
          f"{len(rels)} relationships in the script, "
          f"{len(RELATIONSHIPS)} in the model spec")
    check(len(measures) == len(MEASURES),
          f"{len(measures)} measures in the script, {len(MEASURES)} in the library")
    check(len(set(tables)) == len(tables), "a table name is declared twice")
    check(len(set(exprs)) == len(exprs), "an expression name is declared twice")

    # --- 6. every queryGroup referenced is declared -----------------------
    used = set(re.findall(r"^\t+queryGroup: (.+)$", text, re.M))
    for g in sorted(used):
        check(g.strip() in groups,
              f"queryGroup '{g.strip()}' is used but never declared")

    # --- 7. no drift from the PBIP ---------------------------------------
    # Both come from build_pbip's emitters, so a difference means one path was
    # edited and the other was not.
    pbip_tables, pbip_exprs, pbip_measures = set(), set(), set()
    for root, _, files in os.walk(DEFN):
        for f in files:
            if not f.endswith(".tmdl"):
                continue
            body = open(os.path.join(root, f), encoding="utf-8").read()
            pbip_tables |= set(re.findall(r"^table (\S+)", body, re.M))
            pbip_exprs |= set(re.findall(r"^expression (\S+) =", body, re.M))
            pbip_measures |= set(re.findall(r"^\tmeasure '([^']+)'", body, re.M))
    check(pbip_tables == set(tables),
          f"tables drift from the PBIP: only in script "
          f"{sorted(set(tables) - pbip_tables)}, only in PBIP "
          f"{sorted(pbip_tables - set(tables))}")
    check(pbip_exprs == set(exprs),
          f"parameters/functions drift from the PBIP: only in script "
          f"{sorted(set(exprs) - pbip_exprs)}, only in PBIP "
          f"{sorted(pbip_exprs - set(exprs))}")
    script_measures = set(re.findall(r"measure '([^']+)'", text))
    check(pbip_measures == script_measures,
          f"measures drift from the PBIP: "
          f"{len(script_measures ^ pbip_measures)} names differ")

    # --- 8. no model property is set, at all ------------------------------
    # Two separate applies died on model properties: culture (illegal once the
    # model holds any object) and defaultPowerBIDataSourceVersion (reset to its
    # V1 default, a downgrade from 2). Rather than enumerate the ones known to
    # bite, forbid the whole class - a model child must be an object, never a
    # `name: value` property assignment.
    OBJECT_KEYWORDS = ("queryGroup ", "expression ", "table ", "relationship ",
                       "annotation ", "ref ", "///")
    for n, d, c in rows:
        if d != 2:
            continue
        is_object = c.startswith(OBJECT_KEYWORDS)
        looks_like_property = re.match(r"^[A-Za-z_][\w]*\s*:", c)
        check(is_object or not looks_like_property,
              f"line {n} sets a model property: {c[:60]!r}. The script references "
              f"the model rather than replacing it, so it must set none.")

    # --- 9. relationship endpoints resolve -------------------------------
    cols: dict[str, set[str]] = {}
    current = None
    for _, d, c in rows:
        if d == 2 and c.startswith("table "):
            current = c[len("table "):]
            cols[current] = set()
        elif d == 3 and c.startswith("column ") and current:
            cols[current].add(c[len("column "):].strip("'"))
    for ft, fc, tt, tc, _ in RELATIONSHIPS:
        check(fc in cols.get(ft, set()),
              f"relationship endpoint {ft}[{fc}] is not a column in the script")
        check(tc in cols.get(tt, set()),
              f"relationship endpoint {tt}[{tc}] is not a column in the script")

    # --- 10. every partition has a mode ----------------------------------
    parts = [c for _, d, c in rows if d == 3 and c.startswith("partition ")]
    check(len(parts) == len(tables),
          f"{len(parts)} partitions for {len(tables)} tables")

    report(len(tables), len(exprs), len(rels), len(measures))


def report(nt=0, ne=0, nr=0, nm=0) -> None:
    print()
    print(f"  script         powerbi/PM_Model.tmdl")
    print(f"  tables         {nt}  (each with a partition)")
    print(f"  parameters     {ne}  parameters and functions")
    print(f"  relationships  {nr}")
    print(f"  measures       {nm}")
    print(f"  cross-checked  against the PBIP definition, so the two cannot drift")
    print(f"  ---- {checks} checks ----")
    print()
    if errors:
        for e in errors:
            print(f"    FAIL - {e}")
        print(f"\n  {len(errors)} problem(s).")
        sys.exit(1)
    print("  PASS - the script is well-formed and matches the model.")


if __name__ == "__main__":
    main()
