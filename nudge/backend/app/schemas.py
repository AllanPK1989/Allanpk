"""Request bodies."""
import datetime as dt
from datetime import date, time

from pydantic import BaseModel, Field


class PinIn(BaseModel):
    pin: str = Field(min_length=4, max_length=8)


class PinChangeIn(BaseModel):
    current_pin: str
    new_pin: str = Field(min_length=4, max_length=8)


class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    notes: str = ""
    basket_id: int | None = None
    priority: str = "normal"
    due_date: date | None = None
    due_time: time | None = None
    person: str = ""
    status: str = "open"  # open | waiting
    repeat_rule: str = ""
    nudge_every_days: int | None = None
    checklist: list[str] = []
    focus: bool = False
    inbox: bool = False
    transcript: str = ""
    source: str = "manual"
    ai_fields: list[str] = []


class TaskPatch(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    notes: str | None = None
    basket_id: int | None = None
    priority: str | None = None
    due_date: date | None = None
    due_time: time | None = None
    person: str | None = None
    status: str | None = None
    repeat_rule: str | None = None
    nudge_every_days: int | None = None
    confirm_ai: bool | None = None
    inbox: bool | None = None


class FollowUpIn(BaseModel):
    in_days: int | None = Field(default=None, ge=0, le=365)
    date: dt.date | None = None
    title: str | None = None
    person: str | None = None


class CloseIn(BaseModel):
    note: str = ""
    follow_up: FollowUpIn | None = None


class SnoozeIn(BaseModel):
    preset: str
    date: dt.date | None = None
    time: dt.time | None = None


class FocusIn(BaseModel):
    on: bool = True


class BulkIn(BaseModel):
    ids: list[int] = Field(max_length=500)
    action: str  # tomorrow | done | drop | basket
    basket_id: int | None = None


class ChecklistItemIn(BaseModel):
    text: str = Field(min_length=1, max_length=300)


class ChecklistItemPatch(BaseModel):
    text: str | None = Field(default=None, max_length=300)
    done: bool | None = None


class BasketIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    color: str = "blue"
    icon: str = "briefcase"


class BasketPatch(BaseModel):
    name: str | None = Field(default=None, max_length=60)
    color: str | None = None
    icon: str | None = None
    archived: bool | None = None


class ReorderIn(BaseModel):
    ids: list[int]


class InterpretIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class DraftIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    notes: str = ""
    basket_id: int | None = None
    due_date: date | None = None
    due_time: time | None = None
    priority: str = "normal"
    person: str = ""
    waiting: bool = False
    repeat_rule: str = ""
    checklist: list[str] = []
    guessed: list[str] = []


class TargetIn(BaseModel):
    task_id: int
    due_date: date | None = None
    due_time: time | None = None


class ApplyIn(BaseModel):
    intent: str  # create | complete | reschedule
    transcript: str = ""
    source: str = "voice"
    drafts: list[DraftIn] = []
    targets: list[TargetIn] = []
    keep_guesses: bool = False  # True for offline captures nobody has reviewed yet


class PushSubIn(BaseModel):
    endpoint: str
    keys: dict[str, str]


class PushUnsubIn(BaseModel):
    endpoint: str


class PushActionIn(BaseModel):
    token: str
    action: str  # done | snooze_1h | tomorrow | nudged
