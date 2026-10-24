"""Database tables. See SPEC.md section 6 for the design notes.

Rules that the code relies on:
- No hard deletes. Deactivate (active=False), reject or retire instead.
- Every change goes through app/audit.py.
- A technician's own words live in LogText.original and are never overwritten by the AI.
"""
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

JSONType = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """Timezone-aware UTC datetimes on every database (SQLite returns naive values)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc) if value is not None else None

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)


# Allowed values, kept as plain strings so the database stays easy to read and export.
ROLES = ("technician", "supervisor", "admin")
LANGS = ("en", "ta")
CRITICALITY = ("A", "B", "C")
MACHINE_STATUS = ("running", "down", "maintenance", "retired")
LOG_STATUS = ("draft", "open", "closed", "verified", "rejected")
LOG_SOURCE = ("voice", "text", "ai_session", "import")
TEXT_FIELDS = ("issue", "root_cause", "corrective_action")
COMPONENT_CATEGORIES = ("pneumatic", "electrical", "sensor", "plc", "mechanical", "other")
FAULT_CARD_STATUS = ("draft", "approved", "needs_review", "retired")


class MachineType(Timestamps, Base):
    __tablename__ = "machine_types"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")


class Machine(Timestamps, Base):
    __tablename__ = "machines"
    id: Mapped[int] = mapped_column(primary_key=True)
    machine_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    machine_type_id: Mapped[int | None] = mapped_column(ForeignKey("machine_types.id"))
    zone: Mapped[str] = mapped_column(String(80), default="", index=True)
    line: Mapped[str] = mapped_column(String(80), default="")
    make: Mapped[str] = mapped_column(String(120), default="")
    model: Mapped[str] = mapped_column(String(120), default="")
    plc_model: Mapped[str] = mapped_column(String(120), default="")
    key_components: Mapped[str] = mapped_column(Text, default="")
    criticality: Mapped[str] = mapped_column(String(1), default="B")
    status: Mapped[str] = mapped_column(String(20), default="running")
    qr_code: Mapped[str] = mapped_column(String(300), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    machine_type: Mapped[MachineType | None] = relationship()
    components: Mapped[list["Component"]] = relationship(back_populates="machine")


class Component(Timestamps, Base):
    __tablename__ = "components"
    id: Mapped[int] = mapped_column(primary_key=True)
    machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(20), default="other")
    part_no: Mapped[str] = mapped_column(String(80), default="")
    make: Mapped[str] = mapped_column(String(120), default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    machine: Mapped[Machine] = relationship(back_populates="components")


class User(Timestamps, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20), default="technician")
    zone: Mapped[str] = mapped_column(String(80), default="")
    preferred_language: Mapped[str] = mapped_column(String(2), default="ta")
    skill_level: Mapped[str] = mapped_column(String(40), default="")
    phone: Mapped[str] = mapped_column(String(30), default="")
    pin_hash: Mapped[str] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class AISession(Base):
    __tablename__ = "ai_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id"), index=True)
    technician_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    language: Mapped[str] = mapped_column(String(2), default="en")
    problem_text: Mapped[str] = mapped_column(Text, default="")
    alarm_code: Mapped[str] = mapped_column(String(60), default="")
    questions_and_answers: Mapped[list] = mapped_column(JSONType, default=list)
    steps: Mapped[list] = mapped_column(JSONType, default=list)
    step_responses: Mapped[list] = mapped_column(JSONType, default=list)
    sources_used: Mapped[list] = mapped_column(JSONType, default=list)
    procedure_meta: Mapped[dict] = mapped_column(JSONType, default=dict)
    model: Mapped[str] = mapped_column(String(80), default="")
    prompt_version: Mapped[str] = mapped_column(String(40), default="")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    # in_progress | resolved | escalated | refused | failed | abandoned
    outcome: Mapped[str] = mapped_column(String(20), default="in_progress", index=True)
    feedback: Mapped[str] = mapped_column(String(20), default="")  # helpful | not_helpful
    feedback_note: Mapped[str] = mapped_column(Text, default="")
    # Plain integer (no FK) to avoid a circular reference with breakdown_logs.ai_session_id.
    resulting_log_id: Mapped[int | None] = mapped_column(Integer, index=True)
    supervisor_called: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    machine: Mapped[Machine] = relationship()
    technician: Mapped[User] = relationship()


class BreakdownLog(Timestamps, Base):
    __tablename__ = "breakdown_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    log_no: Mapped[str] = mapped_column(String(30), unique=True, index=True, default="")
    machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id"), index=True)
    technician_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    technician_name: Mapped[str] = mapped_column(String(120), default="")  # imports may name people not in users
    zone: Mapped[str] = mapped_column(String(80), default="")
    shift: Mapped[str] = mapped_column(String(10), default="")
    shift_date: Mapped[date | None] = mapped_column(Date, index=True)
    reported_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    start_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    end_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    downtime_min: Mapped[int | None] = mapped_column(Integer)
    alarm_code: Mapped[str] = mapped_column(String(60), default="")
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    verified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    verified_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    reject_reason: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(20), default="text")
    ai_session_id: Mapped[int | None] = mapped_column(ForeignKey("ai_sessions.id"))
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    # True while AI-filled fields wait for the technician (offline voice logs, session drafts).
    needs_confirmation: Mapped[bool] = mapped_column(Boolean, default=False)
    client_uuid: Mapped[str | None] = mapped_column(String(64), unique=True)
    original_language: Mapped[str] = mapped_column(String(10), default="")
    enriched_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    machine: Mapped[Machine] = relationship()
    technician: Mapped[User | None] = relationship(foreign_keys=[technician_id])
    verifier: Mapped[User | None] = relationship(foreign_keys=[verified_by])
    texts: Mapped[list["LogText"]] = relationship(back_populates="log", order_by="LogText.id")
    parts: Mapped[list["LogPart"]] = relationship(back_populates="log", order_by="LogPart.id")
    media: Mapped[list["LogMedia"]] = relationship(
        back_populates="log", foreign_keys="LogMedia.log_id", order_by="LogMedia.id"
    )
    classification: Mapped["LogClassification | None"] = relationship(back_populates="log")

    def text(self, field: str, lang: str = "en") -> str:
        """Best available version of a text field in the asked language."""
        for t in self.texts:
            if t.field == field:
                preferred = t.english if lang == "en" else t.tamil
                return preferred or t.original or ""
        return ""

    def original(self, field: str) -> str:
        for t in self.texts:
            if t.field == field:
                return t.original
        return ""


class LogText(Base):
    __tablename__ = "log_texts"
    __table_args__ = (UniqueConstraint("log_id", "field"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    log_id: Mapped[int] = mapped_column(ForeignKey("breakdown_logs.id"), index=True)
    field: Mapped[str] = mapped_column(String(30))
    original: Mapped[str] = mapped_column(Text, default="")
    original_lang: Mapped[str] = mapped_column(String(10), default="")  # en | ta | mixed
    english: Mapped[str] = mapped_column(Text, default="")
    tamil: Mapped[str] = mapped_column(Text, default="")
    ai_filled: Mapped[bool] = mapped_column(Boolean, default=False)  # true until the technician confirms
    ai_unsure: Mapped[bool] = mapped_column(Boolean, default=False)  # highlight for checking
    translated_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    log: Mapped[BreakdownLog] = relationship(back_populates="texts")


class LogMedia(Base):
    __tablename__ = "log_media"
    id: Mapped[int] = mapped_column(primary_key=True)
    log_id: Mapped[int | None] = mapped_column(ForeignKey("breakdown_logs.id"), index=True)
    ai_session_id: Mapped[int | None] = mapped_column(ForeignKey("ai_sessions.id"), index=True)
    kind: Mapped[str] = mapped_column(String(10))  # audio | photo
    file_path: Mapped[str] = mapped_column(String(400))
    mime: Mapped[str] = mapped_column(String(80), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    transcript: Mapped[str] = mapped_column(Text, default="")
    stt_provider: Mapped[str] = mapped_column(String(40), default="")
    confidence: Mapped[float | None] = mapped_column(Float)
    language: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(20), default="stored")  # stored | transcribed | failed
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime, index=True)
    purged_at: Mapped[datetime | None] = mapped_column(UTCDateTime)  # file removed, row kept

    log: Mapped[BreakdownLog | None] = relationship(back_populates="media", foreign_keys=[log_id])


class LogPart(Base):
    __tablename__ = "log_parts"
    id: Mapped[int] = mapped_column(primary_key=True)
    log_id: Mapped[int] = mapped_column(ForeignKey("breakdown_logs.id"), index=True)
    part_no: Mapped[str] = mapped_column(String(80), default="")
    description: Mapped[str] = mapped_column(String(300), default="")
    qty: Mapped[float] = mapped_column(Float, default=1)

    log: Mapped[BreakdownLog] = relationship(back_populates="parts")


class LogClassification(Base):
    __tablename__ = "log_classification"
    id: Mapped[int] = mapped_column(primary_key=True)
    log_id: Mapped[int] = mapped_column(ForeignKey("breakdown_logs.id"), unique=True)
    symptom_category: Mapped[str] = mapped_column(String(120), default="")
    component_id: Mapped[int | None] = mapped_column(ForeignKey("components.id"))
    component_name: Mapped[str] = mapped_column(String(200), default="")
    failure_mode: Mapped[str] = mapped_column(String(200), default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    edited_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    log: Mapped[BreakdownLog] = relationship(back_populates="classification")


class AICall(Base):
    __tablename__ = "ai_calls"
    id: Mapped[int] = mapped_column(primary_key=True)
    purpose: Mapped[str] = mapped_column(String(40), index=True)
    provider: Mapped[str] = mapped_column(String(20), default="")
    model: Mapped[str] = mapped_column(String(80), default="")
    prompt_version: Mapped[str] = mapped_column(String(40), default="")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_write_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    error: Mapped[str] = mapped_column(Text, default="")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    ai_session_id: Mapped[int | None] = mapped_column(ForeignKey("ai_sessions.id"))
    log_id: Mapped[int | None] = mapped_column(ForeignKey("breakdown_logs.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)


class FaultCard(Timestamps, Base):
    __tablename__ = "fault_cards"
    id: Mapped[int] = mapped_column(primary_key=True)
    machine_id: Mapped[int | None] = mapped_column(ForeignKey("machines.id"), index=True)
    machine_type_id: Mapped[int | None] = mapped_column(ForeignKey("machine_types.id"), index=True)
    symptom: Mapped[str] = mapped_column(Text)
    symptom_ta: Mapped[str] = mapped_column(Text, default="")
    causes: Mapped[list] = mapped_column(JSONType, default=list)  # [{"cause": str, "count": int}]
    steps_en: Mapped[list] = mapped_column(JSONType, default=list)  # [str]
    steps_ta: Mapped[list] = mapped_column(JSONType, default=list)
    parts: Mapped[list] = mapped_column(JSONType, default=list)
    tools: Mapped[list] = mapped_column(JSONType, default=list)
    avg_fix_min: Mapped[int | None] = mapped_column(Integer)
    source_log_ids: Mapped[list] = mapped_column(JSONType, default=list)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class Glossary(Timestamps, Base):
    __tablename__ = "glossary"
    id: Mapped[int] = mapped_column(primary_key=True)
    term_en: Mapped[str] = mapped_column(String(200), index=True)
    term_ta: Mapped[str] = mapped_column(String(200), default="")
    spoken_variants: Mapped[list] = mapped_column(JSONType, default=list)
    category: Mapped[str] = mapped_column(String(60), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class TranslationCache(Base):
    __tablename__ = "translation_cache"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)
    target_lang: Mapped[str] = mapped_column(String(2))
    source_text: Mapped[str] = mapped_column(Text)
    translated: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict | list | int | float | str | None] = mapped_column(JSONType)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    entity: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[str] = mapped_column(String(40), index=True)
    action: Mapped[str] = mapped_column(String(40))
    before: Mapped[dict | None] = mapped_column(JSONType)
    after: Mapped[dict | None] = mapped_column(JSONType)
    at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
