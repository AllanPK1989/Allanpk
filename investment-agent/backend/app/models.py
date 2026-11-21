"""Database tables."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Asset classes the app knows about.
ASSET_CLASSES = ("stock", "etf", "mutual_fund", "crypto", "index", "commodity", "forex", "bond")


class Instrument(Base):
    """Anything the owner has searched for, holds or watches.

    `symbol` is the app-wide key: a Yahoo symbol (RELIANCE.NS, AAPL, GC=F, USDINR=X, ^NSEI),
    "MF:<AMFI scheme code>" for Indian mutual funds, or "CRYPTO:<PAIR>" for Crypto.com pairs.
    Every searched instrument stays followed until the owner removes it.
    """

    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    asset_class: Mapped[str] = mapped_column(String(32))
    region: Mapped[str] = mapped_column(String(16), default="GLOBAL")
    exchange: Mapped[str] = mapped_column(String(64), default="")
    currency: Mapped[str] = mapped_column(String(8), default="")
    followed: Mapped[bool] = mapped_column(Boolean, default=True)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(32), default="search")  # search | watchlist | portfolio | agent
    alert_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    search_count: Mapped[int] = mapped_column(Integer, default=0)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    transactions: Mapped[list[Transaction]] = relationship(back_populates="instrument", cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="CASCADE"), index=True)
    side: Mapped[str] = mapped_column(String(4))  # buy | sell
    quantity: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)  # per unit, in the instrument's currency
    trade_date: Mapped[date] = mapped_column(Date)
    fees: Mapped[float] = mapped_column(Float, default=0.0)
    # INR per unit of the trade currency on the trade date (foreign assets). None = use today's rate.
    fx_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    instrument: Mapped[Instrument] = relationship(back_populates="transactions")


news_instruments = Table(
    "news_instruments",
    Base.metadata,
    Column("news_id", ForeignKey("news.id", ondelete="CASCADE"), primary_key=True),
    Column("instrument_id", ForeignKey("instruments.id", ondelete="CASCADE"), primary_key=True),
)


class NewsItem(Base):
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # hash of normalised url/title
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(128), default="")
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    snippet: Mapped[str] = mapped_column(Text, default="")
    scope: Mapped[str] = mapped_column(String(16), default="instrument")  # instrument | market
    # Filled in by the news model:
    summary: Mapped[str] = mapped_column(Text, default="")
    sentiment: Mapped[str] = mapped_column(String(16), default="")
    impact: Mapped[str] = mapped_column(String(8), default="")
    category: Mapped[str] = mapped_column(String(32), default="")
    summarized: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    alerted: Mapped[bool] = mapped_column(Boolean, default=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    instruments: Mapped[list[Instrument]] = relationship(secondary=news_instruments)


class Digest(Base):
    __tablename__ = "digests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), index=True)  # morning | evening | weekly | alert
    title: Mapped[str] = mapped_column(String(256))
    markdown: Mapped[str] = mapped_column(Text)
    html: Mapped[str] = mapped_column(Text)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pushed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Report(Base):
    """A saved AI analysis of one instrument."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="CASCADE"), index=True)
    verdict: Mapped[str] = mapped_column(String(32), default="")
    markdown: Mapped[str] = mapped_column(Text)
    html: Mapped[str] = mapped_column(Text)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AlertLog(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(160), unique=True)  # de-duplication key
    kind: Mapped[str] = mapped_column(String(16))  # price | news
    instrument_id: Mapped[int | None] = mapped_column(ForeignKey("instruments.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(256))
    body: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    endpoint: Mapped[str] = mapped_column(Text, unique=True)
    p256dh: Mapped[str] = mapped_column(String(256))
    auth: Mapped[str] = mapped_column(String(128))
    user_agent: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    failures: Mapped[int] = mapped_column(Integer, default=0)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), default="New chat")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.id"
    )


class ChatMessage(Base):
    """One API message, stored exactly as sent/received so history can be replayed unchanged."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # user | assistant
    content: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped[ChatSession] = relationship(back_populates="messages")


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON)


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(16), default="running")  # running | ok | error
    detail: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
