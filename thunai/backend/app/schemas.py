"""Request bodies for the REST API. Responses are built in serialize.py."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Lang = Literal["en", "ta"]


class LoginIn(BaseModel):
    employee_id: str = Field(min_length=1, max_length=40)
    pin: str = Field(min_length=4, max_length=4)
    shared_device: bool = False


class MeUpdate(BaseModel):
    preferred_language: Lang


class TextIn(BaseModel):
    original: str = ""
    en: str | None = None
    ta: str | None = None
    ai_filled: bool = False
    unsure: bool = False


class PartIn(BaseModel):
    part_no: str = ""
    description: str = ""
    qty: float = 1


class LogIn(BaseModel):
    machine_no: str
    issue: TextIn = TextIn()
    root_cause: TextIn = TextIn()
    corrective_action: TextIn = TextIn()
    start_at: datetime | None = None
    end_at: datetime | None = None
    downtime_min: int | None = None
    alarm_code: str = ""
    parts: list[PartIn] = []
    source: Literal["voice", "text", "ai_session"] = "text"
    ai_session_id: int | None = None
    media_ids: list[int] = []
    client_uuid: str | None = Field(default=None, max_length=64)
    submit: bool = True
    still_down: bool = False


class LogUpdate(BaseModel):
    issue: TextIn | None = None
    root_cause: TextIn | None = None
    corrective_action: TextIn | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    downtime_min: int | None = None
    alarm_code: str | None = None
    parts: list[PartIn] | None = None
    media_ids: list[int] = []
    submit: bool = False
    still_down: bool = False
    append_note: str = ""  # adding to an existing open log


class ExtractIn(BaseModel):
    machine_no: str
    transcript: str = Field(min_length=1, max_length=5000)


class RejectIn(BaseModel):
    reason: str = Field(min_length=2, max_length=500)


class SessionStart(BaseModel):
    machine_no: str
    problem_text: str = Field(min_length=2, max_length=3000)
    language: Lang = "en"
    alarm_code: str = ""
    media_ids: list[int] = []


class AnswersIn(BaseModel):
    answers: dict[str, str] = {}


class StepResponseIn(BaseModel):
    step_no: int
    response: Literal["ok", "not_ok", "cant_do"]


class ExplainIn(BaseModel):
    step_no: int


class CloseIn(BaseModel):
    running: bool


class FeedbackIn(BaseModel):
    feedback: Literal["helpful", "not_helpful"]
    note: str = ""


class MachineIn(BaseModel):
    machine_no: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    machine_type: str = ""
    zone: str = ""
    line: str = ""
    make: str = ""
    model: str = ""
    plc_model: str = ""
    key_components: str = ""
    criticality: Literal["A", "B", "C"] = "B"
    status: Literal["running", "down", "maintenance", "retired"] = "running"
    notes: str = ""
    active: bool = True

    @field_validator("machine_no")
    @classmethod
    def clean_no(cls, v: str) -> str:
        return v.strip().upper()


class MachineUpdate(BaseModel):
    name: str | None = None
    machine_type: str | None = None
    zone: str | None = None
    line: str | None = None
    make: str | None = None
    model: str | None = None
    plc_model: str | None = None
    key_components: str | None = None
    criticality: Literal["A", "B", "C"] | None = None
    status: Literal["running", "down", "maintenance", "retired"] | None = None
    notes: str | None = None
    active: bool | None = None


class ComponentIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: Literal["pneumatic", "electrical", "sensor", "plc", "mechanical", "other"] = "other"
    part_no: str = ""
    make: str = ""
    location: str = ""
    active: bool = True


class UserIn(BaseModel):
    employee_id: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=120)
    role: Literal["technician", "supervisor", "admin"] = "technician"
    zone: str = ""
    preferred_language: Lang = "ta"
    skill_level: str = ""
    phone: str = ""
    pin: str = Field(min_length=4, max_length=4)


class UserUpdate(BaseModel):
    name: str | None = None
    role: Literal["technician", "supervisor", "admin"] | None = None
    zone: str | None = None
    preferred_language: Lang | None = None
    skill_level: str | None = None
    phone: str | None = None
    active: bool | None = None


class PinReset(BaseModel):
    pin: str = Field(min_length=4, max_length=4)


class GlossaryIn(BaseModel):
    term_en: str = Field(min_length=1, max_length=200)
    term_ta: str = ""
    spoken_variants: list[str] = []
    category: str = ""
    active: bool = True


class SettingIn(BaseModel):
    value: dict | list | int | float | str | bool | None


class CauseEdit(BaseModel):
    cause: str = Field(min_length=1, max_length=300)
    cause_ta: str = ""


class FaultCardEdit(BaseModel):
    symptom: str | None = Field(default=None, min_length=1, max_length=300)
    symptom_ta: str | None = None
    causes: list[CauseEdit] | None = None  # counts stay as computed from the logs
    steps_en: list[str] | None = None
    steps_ta: list[str] | None = None
    parts: list[str] | None = None
    tools: list[str] | None = None


class ReasonIn(BaseModel):
    reason: str = Field(default="", max_length=500)


class TipIn(BaseModel):
    machine_no: str
    text: str = Field(min_length=2, max_length=2000)  # the technician's own words
    media_id: int | None = None
