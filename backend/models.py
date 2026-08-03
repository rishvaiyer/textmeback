from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db import Base


class Contact(Base):
    __tablename__ = "contacts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    display_name: Mapped[str] = mapped_column(String(255))
    handle: Mapped[str] = mapped_column(String(255), index=True)
    usual_tone: Mapped[str | None] = mapped_column(String(50))
    relationship_label: Mapped[str | None] = mapped_column(String(100))
    excluded_from_analytics: Mapped[bool] = mapped_column(Boolean, default=False)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    threads: Mapped[list["Thread"]] = relationship(back_populates="contact")


class Thread(Base):
    __tablename__ = "threads"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_type: Mapped[str] = mapped_column(String(50), default="imessage")
    external_thread_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id"))
    latest_at: Mapped[datetime | None] = mapped_column(DateTime)
    latest_message: Mapped[str | None] = mapped_column(Text)
    needs_response_estimate: Mapped[bool] = mapped_column(Boolean, default=False)
    priority_label: Mapped[str | None] = mapped_column(String(50))
    urgency: Mapped[str | None] = mapped_column(String(20))
    category: Mapped[str | None] = mapped_column(String(50))
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    contact: Mapped["Contact | None"] = relationship(back_populates="threads")
    messages: Mapped[list["Message"]] = relationship(back_populates="thread", cascade="all, delete-orphan")
    drafts: Mapped[list["Draft"]] = relationship(back_populates="thread", cascade="all, delete-orphan")
    followups: Mapped[list["FollowupItem"]] = relationship(back_populates="thread", cascade="all, delete-orphan")
    analytics: Mapped[list["ThreadAnalytics"]] = relationship(back_populates="thread", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("threads.id"))
    external_message_id: Mapped[str | None] = mapped_column(String(255), index=True)
    is_from_me: Mapped[bool] = mapped_column(Boolean, default=False)
    text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime)
    source_type: Mapped[str] = mapped_column(String(50), default="imessage")
    thread: Mapped["Thread"] = relationship(back_populates="messages")


class Draft(Base):
    __tablename__ = "drafts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("threads.id"))
    draft_text: Mapped[str] = mapped_column(Text)
    urgency: Mapped[str | None] = mapped_column(String(20))
    category: Mapped[str | None] = mapped_column(String(50))
    reason: Mapped[str | None] = mapped_column(Text)
    risk_flags_json: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    thread: Mapped["Thread"] = relationship(back_populates="drafts")
    decisions: Mapped[list["Decision"]] = relationship(back_populates="draft", cascade="all, delete-orphan")


class Decision(Base):
    __tablename__ = "decisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("threads.id"))
    draft_id: Mapped[int | None] = mapped_column(ForeignKey("drafts.id"))
    decision_type: Mapped[str] = mapped_column(String(50))
    original_draft: Mapped[str | None] = mapped_column(Text)
    edited_draft: Mapped[str | None] = mapped_column(Text)
    copied_to_clipboard: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    draft: Mapped["Draft | None"] = relationship(back_populates="decisions")


class StyleProfileSnapshot(Base):
    __tablename__ = "style_profile_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_json: Mapped[str] = mapped_column(Text)
    trigger_event: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class FollowupItem(Base):
    __tablename__ = "followup_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("threads.id"))
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id"))
    source_message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id"))
    task_text: Mapped[str] = mapped_column(Text)
    due_date: Mapped[str | None] = mapped_column(String(50))
    direction: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="open")
    confidence: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    thread: Mapped["Thread"] = relationship(back_populates="followups")


class ThreadAnalytics(Base):
    __tablename__ = "thread_analytics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("threads.id"))
    emotional_tone: Mapped[str | None] = mapped_column(String(50))
    tone_trend: Mapped[str | None] = mapped_column(String(50))
    response_status: Mapped[str | None] = mapped_column(String(50))
    open_loops_json: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str | None] = mapped_column(String(20))
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    thread: Mapped["Thread"] = relationship(back_populates="analytics")


class RelationshipSnapshot(Base):
    __tablename__ = "relationship_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"))
    message_volume: Mapped[int] = mapped_column(Integer, default=0)
    last_interaction: Mapped[datetime | None] = mapped_column(DateTime)
    avg_response_hours: Mapped[float | None] = mapped_column(Float)
    unanswered_estimate: Mapped[int] = mapped_column(Integer, default=0)
    user_waiting_on_them: Mapped[int] = mapped_column(Integer, default=0)
    they_waiting_on_user: Mapped[int] = mapped_column(Integer, default=0)
    emotional_tone: Mapped[str | None] = mapped_column(String(50))
    common_topics_json: Mapped[str | None] = mapped_column(Text)
    open_loops_json: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str | None] = mapped_column(String(20))
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class DashboardPreferences(Base):
    __tablename__ = "dashboard_preferences"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    widget_visibility_json: Mapped[str | None] = mapped_column(Text)
    widget_order_json: Mapped[str | None] = mapped_column(Text)
    layout_density: Mapped[str] = mapped_column(String(20), default="spacious")
    default_tab: Mapped[str] = mapped_column(String(50), default="dashboard")
    pinned_contacts_json: Mapped[str | None] = mapped_column(Text)
    pinned_threads_json: Mapped[str | None] = mapped_column(Text)
    inbox_card_fields_json: Mapped[str | None] = mapped_column(Text)
    enabled_tabs_json: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class Export(Base):
    __tablename__ = "exports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    export_type: Mapped[str] = mapped_column(String(50))
    file_path: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class TokenUsageEstimate(Base):
    __tablename__ = "token_usage_estimates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operation_type: Mapped[str] = mapped_column(String(100))
    model_name: Mapped[str | None] = mapped_column(String(100))
    estimated_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class Setting(Base):
    __tablename__ = "settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(255), unique=True)
    value: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
