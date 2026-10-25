"""Request and response shapes of the Copilot tool API (SPEC 13.2).

The descriptions go into the connector's OpenAPI file, and the Copilot orchestrator reads them to
choose a tool and fill its inputs, so they are written for the agent. Missing values are left out
of responses (never null) because the connector's OpenAPI 2.0 has no null type.
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Lang = Literal["en", "ta"]
LANG = Field("en", description="Language of the technician: en (English) or ta (Tamil).")


class In(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


# ---- people and machines -------------------------------------------------------------------------
class Me(BaseModel):
    employee_id: str
    name: str
    role: str = Field(description="technician, supervisor or admin.")
    zone: str
    language: Lang = Field(description="The person's preferred language in Thunai.")


class MachineOut(BaseModel):
    machine_no: str
    name: str
    machine_type: str
    zone: str
    line: str
    status: str = Field(description="running or down, as last logged.")
    active_alarm_code: str = Field("", description="Newest uncleared PLC/SCADA alarm, if any.")


class MachineList(BaseModel):
    machines: list[MachineOut]


class PartOut(BaseModel):
    part_no: str
    description: str
    unit: str
    stock_qty: float | None = Field(None, description="Left out when the stock is not known.")
    location: str = Field(description="Store location.")
    low: bool = Field(description="True when stock is at or below the minimum.")
    stock_text: str = Field(description="Ready text, e.g. '4 pcs in Store A3' or 'Out of stock'.")


class LogSummary(BaseModel):
    log_no: str
    date: str = Field(description="Plant date, YYYY-MM-DD.")
    status: str = Field(description="draft, open (machine still down), closed, verified or rejected.")
    verified: bool
    technician: str
    alarm_code: str
    issue: str = Field(description="English when available, else the technician's words.")
    root_cause: str
    fix: str
    downtime_min: int | None = None


class AlarmOut(BaseModel):
    code: str
    found: bool = Field(description="True when the code is in this machine's alarm list.")
    message: str
    cause: str
    remedy: str
    past_fixes: list[LogSummary] = Field(description="Recent logs on this machine with the same alarm code.")


class FeedRow(BaseModel):
    code: str
    message: str
    count: int = Field(description="Times raised in the last 24 hours.")
    last: datetime
    active: bool


class MachineDetail(BaseModel):
    machine: MachineOut
    active_alarm: AlarmOut | None = Field(None, description="Left out when no PLC/SCADA alarm is active.")
    alarms_24h: list[FeedRow]
    open_logs: list[LogSummary] = Field(description="Breakdowns still open or waiting for confirmation.")
    recent_fixes: list[LogSummary] = Field(description="Last closed or verified breakdowns, newest first.")
    fault_cards: list[str] = Field(description="Approved fault cards for this machine, as 'FC-n: symptom'.")
    low_stock_parts: list[PartOut]


# ---- troubleshooting sessions --------------------------------------------------------------------
class Reading(In):
    label: str = Field(max_length=80, description="What was read, e.g. 'FRL pressure gauge'.")
    value: str = Field("", max_length=40, description="As shown, e.g. '3.5'. Empty when not clearly legible.")
    unit: str = Field("", max_length=20, description="e.g. bar, °C, A.")
    legible: bool = Field(description="True only when the value is clearly readable. Never guess.")


class PhotoIn(In):
    shows: str = Field(max_length=300, description="In English: what the photo shows, e.g. 'HMI alarm screen of the press'.")
    readings: list[Reading] = Field(default_factory=list, max_length=10)
    screen_text: str = Field("", max_length=500, description="Text on an HMI or display, copied as written.")
    alarm_codes: list[str] = Field(default_factory=list, max_length=5, description="Alarm codes visible on a screen.")
    damage: str = Field("", max_length=300, description="In English: visible damage, if any.")


class NewSession(In):
    machine_no: str = Field(max_length=60, description="Machine number, e.g. DEMO-SF-01. Use findMachines if unsure.")
    problem: str = Field(min_length=3, max_length=2000, description="The technician's description, in their own words.")
    alarm_code: str = Field("", max_length=60, description="Alarm code shown on the HMI, if any.")
    language: Lang = LANG
    photos: list[PhotoIn] = Field(
        default_factory=list, max_length=3, description="What you read from photos the technician sent. Leave empty if none."
    )


class Option(BaseModel):
    value: str
    label: str


class Question(BaseModel):
    id: str
    text: str
    options: list[Option]


class Answer(In):
    question_id: str
    value: str = Field(description="One of the question's option values; 'skipped' if the technician does not know.")


class Answers(In):
    answers: list[Answer] = Field(max_length=5)


class Evidence(BaseModel):
    ref: str = Field(description="Source reference, e.g. FC-3, BL-2026-000012, ALARM-A101, PHOTO-1.")
    label: str = Field(description="What kind of source this is.")
    text: str = Field(description="Short English summary of the source.")


class StepOut(BaseModel):
    step_no: int
    total_steps: int
    kind: str = Field(description="safety, check or action.")
    language: Lang = Field(description="Language of the texts below. 'en' when no Tamil version exists yet.")
    action: str
    check: str
    expected_result: str
    safety_note: str
    tools: list[str]
    authorised_only: bool = Field(description="Only an authorised electrician may do this step.")
    general: bool = Field(description="No plant evidence: a general suggestion, not seen on this machine before.")
    evidence: list[Evidence]
    parts: list[PartOut] = Field(description="Catalogue parts named in this step, with live stock.")
    display: str = Field(description="The step ready to show. Show it exactly as written.")


class Cause(BaseModel):
    cause: str
    refs: list[str]


class SessionOut(BaseModel):
    session_id: int
    status: Literal["questions", "step", "finished", "stop", "refused", "failed", "closed"] = Field(
        description=(
            "questions: ask them, then call answerQuestions. step: show current_step and wait for OK, NOT OK or CAN'T DO. "
            "finished: all steps done; ask if the machine runs, then closeSession. stop: tell the technician to stop and call "
            "callSupervisor. refused: show message only. failed: show message and offer callSupervisor. closed: session is over."
        )
    )
    machine_no: str
    problem: str
    alarm_code: str
    language: Lang
    message: str = Field("", description="Show this to the technician when it is not empty.")
    summary: str = ""
    likely_causes: list[Cause] = Field(default_factory=list)
    low_confidence: bool = False
    questions: list[Question] = Field(default_factory=list)
    current_step: StepOut | None = Field(None, description="The step to show now. Left out when there is none.")
    steps_done: int = 0
    agent_note: str = Field("", description="What to do next. For the agent; do not show it.")


class StepResult(In):
    step_no: int = Field(ge=1, description="The step the technician answered (current_step.step_no).")
    result: Literal["ok", "not_ok", "cant_do"] = Field(
        description="ok: result as expected. not_ok: result not as expected. cant_do: the technician cannot do this step."
    )


class PartUsed(In):
    part_no: str = Field("", max_length=80)
    description: str = Field("", max_length=200)
    qty: float = Field(1, ge=0, le=10000)


class CloseSession(In):
    running: bool = Field(description="True when the machine runs again; false when it is still down.")
    what_fixed_it: str = Field("", max_length=2000, description="The technician's own words: what fixed it (or what was tried).")
    what_fixed_it_en: str = Field("", max_length=2000, description="English version, when the words above are not English.")
    root_cause: str = Field("", max_length=2000, description="The technician's own words: the cause, if known.")
    root_cause_en: str = Field("", max_length=2000, description="English version, when the words above are not English.")
    parts_used: list[PartUsed] = Field(default_factory=list, max_length=20)
    confirmed: bool = Field(
        False, description="True only after you read the log back to the technician and they agreed. Otherwise a draft is saved."
    )


class Supervisor(BaseModel):
    name: str
    phone: str
    zone: str


class ClosedSession(BaseModel):
    log_no: str
    log_status: str = Field(description="closed (saved), draft (technician must confirm in the Thunai app) or open (machine still down).")
    outcome: str = Field(description="resolved or escalated.")
    supervisors: list[Supervisor]
    summary: str = Field(description="Text to send to the supervisor when the machine is still down.")
    message: str


class SupervisorHelp(BaseModel):
    summary: str = Field(description="Ready text to send to the supervisor.")
    supervisors: list[Supervisor]
    message: str


# ---- logs, parts, safety, translation ------------------------------------------------------------
class NewLog(In):
    machine_no: str = Field(max_length=60)
    issue: str = Field(min_length=3, max_length=2000, description="The technician's own words: what was wrong.")
    issue_en: str = Field("", max_length=2000, description="English version, when the words above are not English.")
    corrective_action: str = Field(min_length=3, max_length=2000, description="The technician's own words: what they did.")
    corrective_action_en: str = Field("", max_length=2000)
    root_cause: str = Field("", max_length=2000, description="The technician's own words: the cause, if known.")
    root_cause_en: str = Field("", max_length=2000)
    alarm_code: str = Field("", max_length=60)
    start_at: datetime | None = Field(None, description="When the breakdown started (ISO 8601 with time zone).")
    end_at: datetime | None = Field(None, description="When the machine ran again.")
    downtime_min: int | None = Field(None, ge=0, le=100000, description="Only when start and end times are not known.")
    parts_used: list[PartUsed] = Field(default_factory=list, max_length=20)
    still_down: bool = Field(False, description="True when the machine is still down after this work.")
    confirmed: bool = Field(description="Must be true: you read the log back to the technician and they agreed.")


class SavedLog(BaseModel):
    log_no: str
    log_status: str
    machine_no: str
    message: str


class PartList(BaseModel):
    parts: list[PartOut]


class SafetyQuestion(In):
    text: str = Field(min_length=1, max_length=4000, description="The instruction or advice you want to give.")
    language: Lang = LANG


class SafetyAnswer(BaseModel):
    allowed: bool
    phrase: str = Field("", description="The unsafe phrase that was found.")
    message: str = Field("", description="When not allowed: show this instead of the instruction.")


class TextToTranslate(BaseModel):
    text_id: int
    log_no: str
    machine_no: str
    field: str = Field(description="issue, root_cause or corrective_action.")
    original: str
    original_lang: str = Field(description="en, ta or mixed.")
    needs: list[Lang] = Field(description="The versions that are missing.")


class TranslationList(BaseModel):
    items: list[TextToTranslate]
    remaining: int = Field(description="More texts waiting after these.")


class Translation(In):
    text_id: int
    en: str = Field("", max_length=2000, description="English version. Plain words; keep technical terms.")
    ta: str = Field("", max_length=2000, description="Tamil version: simple spoken Tamil, technical terms in English.")


class Translations(In):
    items: list[Translation] = Field(max_length=50)


class TranslationsSaved(BaseModel):
    saved: int
    skipped: int
    message: str
