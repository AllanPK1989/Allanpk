"""Emit one createOrReplace TMDL script that builds the whole semantic model.

Power BI Desktop's TMDL view takes a pasted script and applies it, materialising
tables, Power Query expressions, relationships and measures - format strings and
display folders included. That turns the model build from a day of clicking into
one paste, and it is the same metadata the PBIP carries because both come from
build_pbip's emitters.

Script shape is per the TMDL scripts reference: a command verb at column 0, then
the objects indented beneath it. Inside a .tmdl FILE the root object is implicit,
so model children may sit at column 0; inside a SCRIPT they cannot, because
`model Model` is itself indented under the command. The model header is therefore
rebuilt here rather than re-indented out of emit_model().
"""
import itertools
import os
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import build_pbip as B
from pbi_model_spec import TABLES, RELATIONSHIPS
from pbi_measures import MEASURES

T = "\t"
OUT = os.path.join(ROOT, "powerbi", "PM_Model.tmdl")


def indent(block: str, levels: int) -> str:
    """Shift a whole TMDL block right, leaving blank lines empty."""
    pad = T * levels
    return "\n".join(pad + ln if ln.strip() else "" for ln in block.split("\n"))


def model_header() -> list[str]:
    return [
        "createOrReplace",
        "",
        T + "model Model",
        # Setting this to the value the model ALREADY holds is the point. Four
        # applies failed here, and the sequence is what taught the rule:
        #
        #   model Model + culture + powerBI_V3
        #     -> "Culture and Collation properties of the Model object may be
        #         changed only before any other object has been created."
        #   model Model, properties deleted
        #     -> "Power BI Data Source Version is only allowed to change from V1
        #         to a higher version, Current version is '2'"
        #   ref model Model, properties deleted   -> the same
        #   model Model + powerBI_V2              -> the same
        #
        # The second showed that deleting a property does not stop it being
        # written, it makes it DEFAULT: createOrReplace replaces the model object
        # and resets everything not restated. The default is V1, a downgrade, so
        # it fails. The third showed `ref` does not exempt the model from that.
        #
        # The fourth was mine: "Current version is '2'" reports the ENUM ORDINAL,
        # not the version name. The values are powerBI_V1=0, V2=1, V3=2, so '2'
        # means the model is on V3. Reading it as "version 2" produced a script
        # that tried to downgrade V3 -> V2 and failed identically. Add one to the
        # number in the message to get the name.
        #
        # V3 is what a current Desktop creates, so it is also the right default.
        # Culture stays omitted, and that is sound rather than lucky: after it was
        # removed the culture error stopped, which proves its default matches this
        # model's value, so resetting it changes nothing. Collation the same. Only
        # the data source version has a default that differs from a real model's.
        T * 2 + "defaultPowerBIDataSourceVersion: powerBI_V3",
        "",
        # Declared before anything references them; an expression carrying
        # queryGroup: Parameters fails to apply if the group is not here.
        T * 2 + "queryGroup Parameters",
        T * 3 + "annotation PBI_QueryGroupOrder = 0",
        "",
        T * 2 + "queryGroup Functions",
        T * 3 + "annotation PBI_QueryGroupOrder = 1",
        "",
    ]


def build() -> str:
    L = model_header()

    L.append(indent(B.emit_expressions(), 2))
    for spec in TABLES:
        L.append(indent(B.emit_table(spec), 2))
    L.append(indent(B.emit_measures_table(), 2))
    L.append(indent(B.emit_relationships(), 2))

    return "\n".join(L).rstrip() + "\n"


def deterministic_uids() -> None:
    """Make lineage tags reproducible for this artifact.

    build_pbip mints a random uuid4 per object, which is right for a PBIP whose
    tags are its source-control identity. Here it would mean a different file on
    every build, so the packager could not tell a stale script from a fresh one.
    Same tags every run, still unique within the model, still valid TMDL.
    """
    counter = itertools.count()
    ns = uuid.UUID("6f9619ff-8b86-d011-b42d-00c04fc964ff")
    B.uid = lambda: str(uuid.uuid5(ns, f"pm-model-{next(counter)}"))


def main() -> None:
    deterministic_uids()
    # emit_expressions populates EXPRESSION_SPECS as a side effect, and the
    # query order needs the names, so run it before the header is built.
    B.emit_expressions()
    global EXPR_SPECS
    EXPR_SPECS = B.EXPRESSION_SPECS

    script = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8", newline="\r\n").write(script)

    n_meas = script.count("\n" + T * 3 + "measure ")
    print(f"  powerbi/PM_Model.tmdl  ({len(TABLES) + 1} tables, "
          f"{len(EXPR_SPECS)} parameters and functions, "
          f"{len(RELATIONSHIPS)} relationships, {n_meas} measures, "
          f"{len(script.splitlines())} lines)")


EXPR_SPECS: list = []

if __name__ == "__main__":
    main()
