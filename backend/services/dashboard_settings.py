import json
from backend.db import SessionLocal
from backend.models import DashboardPreferences

DEFAULT_WIDGET_ORDER = [
    "needs_reply",
    "high_risk_threads",
    "follow_ups_due",
    "waiting_on_me",
    "waiting_on_them",
    "emotional_threads",
    "work_admin_threads",
    "recent_drafts",
    "overdue_replies",
    "relationship_snapshot",
    "token_usage_estimate",
    "export_status",
    "imessage_sync_status",
]

DEFAULT_WIDGET_VISIBILITY = {w: True for w in DEFAULT_WIDGET_ORDER}

DEFAULT_INBOX_CARD_FIELDS = ["contact", "latest_message", "last_date", "priority_badge", "risk_badge", "needs_response"]

DEFAULT_ENABLED_TABS = ["dashboard", "inbox", "followups", "analytics", "exports", "settings"]


def get_or_create_preferences() -> dict:
    db = SessionLocal()
    try:
        prefs = db.query(DashboardPreferences).first()
        if not prefs:
            prefs = DashboardPreferences(
                widget_visibility_json=json.dumps(DEFAULT_WIDGET_VISIBILITY),
                widget_order_json=json.dumps(DEFAULT_WIDGET_ORDER),
                layout_density="spacious",
                default_tab="dashboard",
                pinned_contacts_json=json.dumps([]),
                pinned_threads_json=json.dumps([]),
                inbox_card_fields_json=json.dumps(DEFAULT_INBOX_CARD_FIELDS),
                enabled_tabs_json=json.dumps(DEFAULT_ENABLED_TABS),
            )
            db.add(prefs)
            db.commit()
            db.refresh(prefs)
        return _serialize(prefs)
    finally:
        db.close()


def update_preferences(data: dict) -> dict:
    db = SessionLocal()
    try:
        prefs = db.query(DashboardPreferences).first()
        if not prefs:
            prefs = DashboardPreferences()
            db.add(prefs)

        if "widget_visibility" in data:
            prefs.widget_visibility_json = json.dumps(data["widget_visibility"])
        if "widget_order" in data:
            prefs.widget_order_json = json.dumps(data["widget_order"])
        if "layout_density" in data:
            prefs.layout_density = data["layout_density"]
        if "default_tab" in data:
            prefs.default_tab = data["default_tab"]
        if "pinned_contacts" in data:
            prefs.pinned_contacts_json = json.dumps(data["pinned_contacts"])
        if "pinned_threads" in data:
            prefs.pinned_threads_json = json.dumps(data["pinned_threads"])
        if "inbox_card_fields" in data:
            prefs.inbox_card_fields_json = json.dumps(data["inbox_card_fields"])
        if "enabled_tabs" in data:
            prefs.enabled_tabs_json = json.dumps(data["enabled_tabs"])

        db.commit()
        db.refresh(prefs)
        return _serialize(prefs)
    finally:
        db.close()


def reset_preferences() -> dict:
    db = SessionLocal()
    try:
        prefs = db.query(DashboardPreferences).first()
        if prefs:
            db.delete(prefs)
            db.commit()
        return get_or_create_preferences()
    finally:
        db.close()


def _serialize(prefs: DashboardPreferences) -> dict:
    return {
        "widget_visibility": json.loads(prefs.widget_visibility_json or "{}"),
        "widget_order": json.loads(prefs.widget_order_json or "[]"),
        "layout_density": prefs.layout_density,
        "default_tab": prefs.default_tab,
        "pinned_contacts": json.loads(prefs.pinned_contacts_json or "[]"),
        "pinned_threads": json.loads(prefs.pinned_threads_json or "[]"),
        "inbox_card_fields": json.loads(prefs.inbox_card_fields_json or "[]"),
        "enabled_tabs": json.loads(prefs.enabled_tabs_json or "[]"),
    }
