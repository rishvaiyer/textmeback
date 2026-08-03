from datetime import datetime
from typing import Any
from pydantic import BaseModel


class MessageOut(BaseModel):
    id: int
    is_from_me: bool
    text: str | None
    created_at: datetime | None
    source_type: str

    class Config:
        from_attributes = True


class ThreadOut(BaseModel):
    id: int
    contact_name: str | None
    latest_at: datetime | None
    latest_message: str | None
    needs_response_estimate: bool
    priority_label: str | None
    urgency: str | None
    category: str | None
    pinned: bool
    source_type: str
    messages: list[MessageOut] = []

    class Config:
        from_attributes = True


class DraftOut(BaseModel):
    id: int
    draft_text: str
    urgency: str | None
    category: str | None
    reason: str | None
    risk_flags_json: str | None
    confidence: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class DecisionIn(BaseModel):
    decision_type: str
    edited_draft: str | None = None


class RewriteIn(BaseModel):
    draft_text: str
    rewrite_type: str
    contact_tone: str = "unknown"


class SettingsIn(BaseModel):
    data: dict[str, Any]


class DashboardPrefsIn(BaseModel):
    data: dict[str, Any]


class FollowupOut(BaseModel):
    id: int
    task_text: str
    direction: str | None
    due_date: str | None
    status: str
    confidence: str | None
    thread_id: int

    class Config:
        from_attributes = True
