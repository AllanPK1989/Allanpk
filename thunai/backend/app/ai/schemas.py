"""Output contracts for every AI call.

The same Pydantic models produce the JSON schema sent to the model (structured outputs) and
validate the reply on the server before anything is shown. Keep fields simple (no min/max
constraints); range checks live in code.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---- clarify ---------------------------------------------------------------------------------
class Option(Strict):
    value: str
    label_en: str
    label_ta: str


class Question(Strict):
    id: str
    text_en: str
    text_ta: str
    options: list[Option]


class ClarifyOut(Strict):
    understood_problem_en: str
    questions: list[Question]


# ---- troubleshoot ----------------------------------------------------------------------------
class Step(Strict):
    step_no: int
    kind: Literal["safety", "check", "action"]
    action_en: str
    action_ta: str
    check_en: str
    check_ta: str
    expected_result_en: str
    expected_result_ta: str
    tools: list[str]
    safety_note_en: str
    safety_note_ta: str
    authorised_only: bool
    if_ok_next: int  # next step number; 0 = procedure finished; -1 = stop and call supervisor
    if_not_ok_next: int
    source_refs: list[str]
    confidence: float


class LikelyCause(Strict):
    cause_en: str
    cause_ta: str
    likelihood: float
    source_refs: list[str]


class TroubleshootOut(Strict):
    summary_en: str
    summary_ta: str
    likely_causes: list[LikelyCause]
    steps: list[Step]
    confidence: float
    refuse: bool  # true when the request itself is unsafe
    refuse_reason_en: str
    refuse_reason_ta: str


class ExplainOut(Strict):
    text_en: str
    text_ta: str


# ---- logs ------------------------------------------------------------------------------------
class FieldValue(Strict):
    original: str  # the technician's own words, copied, not rewritten
    en: str
    ta: str
    unsure: bool


class PartOut(Strict):
    description: str
    part_no: str
    qty: float


class ExtractOut(Strict):
    language: Literal["en", "ta", "mixed"]
    issue: FieldValue
    root_cause: FieldValue
    corrective_action: FieldValue
    parts_replaced: list[PartOut]
    downtime_min: int  # -1 when not said
    start_time: str  # "HH:MM" or ""
    end_time: str
    alarm_code: str
    missing_question_en: str  # one simple question when a mandatory field is missing, else ""
    missing_question_ta: str


class FieldTranslation(Strict):
    field: Literal["issue", "root_cause", "corrective_action"]
    en: str
    ta: str


class EnrichOut(Strict):
    fields: list[FieldTranslation]
    symptom_category: str
    component_name: str
    failure_mode: str
    confidence: float


def strict_schema(model: type[BaseModel]) -> dict:
    """JSON schema with $refs inlined, titles removed and every property required."""
    raw = model.model_json_schema()
    defs = raw.pop("$defs", {})

    def walk(node):
        if isinstance(node, dict):
            if "$ref" in node:
                return walk(defs[node["$ref"].split("/")[-1]])
            out = {k: walk(v) for k, v in node.items() if k not in ("title", "default")}
            if out.get("type") == "object" and "properties" in out:
                out["required"] = list(out["properties"])
                out["additionalProperties"] = False
            if "const" in out:  # single-value Literal
                out["enum"] = [out.pop("const")]
            return out
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    return walk(raw)
