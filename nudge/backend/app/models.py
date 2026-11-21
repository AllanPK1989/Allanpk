"""Tables. All DateTime columns hold naive UTC; due_date/due_time are the user's local wall clock."""
from datetime import date, datetime, time

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base
from .timeutil import utcnow

STATUSES = ("open", "waiting", "done", "dropped")
PRIORITIES = ("high", "normal", "low")


class Basket(Base):
    __tablename__ = "baskets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    color: Mapped[str] = mapped_column(String(20), default="blue")
    icon: Mapped[str] = mapped_column(String(30), default="briefcase")
    position: Mapped[int] = mapped_column(Integer, default=0)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    notes: Mapped[str] = mapped_column(Text, default="")
    basket_id: Mapped[int | None] = mapped_column(ForeignKey("baskets.id", ondelete="SET NULL"), index=True)
    status: Mapped[str] = mapped_column(String(10), default="open", index=True)
    priority: Mapped[str] = mapped_column(String(10), default="normal")

    due_date: Mapped[date | None] = mapped_column(Date, index=True)
    due_time: Mapped[time | None] = mapped_column(Time)
    remind_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    reminded_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Follow-ups: who the task is with, and for "waiting" tasks how often to nudge.
    person: Mapped[str] = mapped_column(String(80), default="", index=True)
    waiting_since: Mapped[datetime | None] = mapped_column(DateTime)
    nudge_every_days: Mapped[int | None] = mapped_column(Integer)
    next_nudge_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    nudge_count: Mapped[int] = mapped_column(Integer, default=0)

    repeat_rule: Mapped[str] = mapped_column(String(200), default="")  # RFC 5545 RRULE
    focus_date: Mapped[date | None] = mapped_column(Date)  # in today's Top 3

    source: Mapped[str] = mapped_column(String(20), default="manual")
    transcript: Mapped[str] = mapped_column(Text, default="")
    ai_fields: Mapped[list] = mapped_column(JSON, default=list)  # AI guesses not yet confirmed
    inbox: Mapped[bool] = mapped_column(Boolean, default=False)  # captured, not yet reviewed
    follows_task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id", ondelete="SET NULL"))

    closed_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    closing_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    stale_prompted_at: Mapped[datetime | None] = mapped_column(DateTime)

    basket: Mapped[Basket | None] = relationship(lazy="joined")
    checklist: Mapped[list["ChecklistItem"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", order_by="ChecklistItem.position", lazy="selectin"
    )


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(String(300))
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, default=0)

    task: Mapped[Task] = relationship(back_populates="checklist")


class TaskEvent(Base):
    """History: created, edited, closed, reopened, snoozed, nudged... Feeds charts and undo."""

    __tablename__ = "task_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    kind: Mapped[str] = mapped_column(String(20))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[object] = mapped_column(JSON)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    user_agent: Mapped[str] = mapped_column(String(300), default="")


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    endpoint: Mapped[str] = mapped_column(Text, unique=True)
    p256dh: Mapped[str] = mapped_column(String(200))
    auth: Mapped[str] = mapped_column(String(100))
    user_agent: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_ok_at: Mapped[datetime | None] = mapped_column(DateTime)
    failures: Mapped[int] = mapped_column(Integer, default=0)


class NotificationLog(Base):
    __tablename__ = "notification_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    kind: Mapped[str] = mapped_column(String(20))  # reminder | nudge | briefing | wrapup | overdue | test
    channel: Mapped[str] = mapped_column(String(10))  # push | email
    task_id: Mapped[int | None] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    delivered: Mapped[int] = mapped_column(Integer, default=0)  # devices / recipients reached
    error: Mapped[str] = mapped_column(Text, default="")

