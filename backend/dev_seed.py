"""Dev-only synthetic seed.

This is NOT a product feature and never ships in the real workflow. It exists
so the analysis pipeline (ranking, tone, follow-ups, analytics, drafts) can be
verified on machines without a macOS Messages database (e.g. CI / Linux).

Run from the `replygraph` directory:
    python -m backend.dev_seed
"""
from datetime import datetime, timedelta

from backend.db import SessionLocal, init_db
from backend.models import (
    Contact, Thread, Message, Draft, Decision, FollowupItem,
    ThreadAnalytics, RelationshipSnapshot, Export, TokenUsageEstimate,
)
from backend.services.ingest import ingest_threads

NOW = datetime(2026, 6, 28, 18, 30, 0)


def ago(mins):
    return NOW - timedelta(minutes=mins)


SEED_THREADS = [
    {
        "thread_id": "seed-1", "contact_name": "Sarah Chen", "handles": ["+15550101"],
        "latest_message": "so are we still on for friday or not? you keep leaving me on read",
        "latest_at": ago(180), "needs_response_estimate": True, "source_type": "imessage",
        "messages": [
            {"message_id": "s1-1", "is_from_me": False, "text": "hey did you get my message about friday?", "created_at": ago(2880), "service": "iMessage"},
            {"message_id": "s1-2", "is_from_me": False, "text": "just need to know if dinner is happening", "created_at": ago(1440), "service": "iMessage"},
            {"message_id": "s1-3", "is_from_me": False, "text": "so are we still on for friday or not? you keep leaving me on read", "created_at": ago(180), "service": "iMessage"},
        ],
    },
    {
        "thread_id": "seed-2", "contact_name": "Dr. Patel office", "handles": ["+15550102"],
        "latest_message": "Please confirm your appointment and whether you want the lab results sent over.",
        "latest_at": ago(600), "needs_response_estimate": True, "source_type": "imessage",
        "messages": [
            {"message_id": "s2-1", "is_from_me": False, "text": "Reminder: follow-up appointment Tue 10:00am.", "created_at": ago(4320), "service": "iMessage"},
            {"message_id": "s2-2", "is_from_me": False, "text": "Please confirm your appointment and whether you want the lab results sent over. This is about your medical results.", "created_at": ago(600), "service": "iMessage"},
        ],
    },
    {
        "thread_id": "seed-3", "contact_name": "Dad", "handles": ["+15550103"],
        "latest_message": "miss you kiddo, call me when you get a chance",
        "latest_at": ago(300), "needs_response_estimate": True, "source_type": "imessage",
        "messages": [
            {"message_id": "s3-1", "is_from_me": False, "text": "how did the presentation go??", "created_at": ago(2000), "service": "iMessage"},
            {"message_id": "s3-2", "is_from_me": True, "text": "went well! tell you about it soon", "created_at": ago(1900), "service": "iMessage"},
            {"message_id": "s3-3", "is_from_me": False, "text": "miss you kiddo, love you, call me when you get a chance", "created_at": ago(300), "service": "iMessage"},
        ],
    },
    {
        "thread_id": "seed-4", "contact_name": "Priya (work)", "handles": ["+15550104"],
        "latest_message": "can you send the revised budget before the client call tomorrow?",
        "latest_at": ago(120), "needs_response_estimate": True, "source_type": "imessage",
        "messages": [
            {"message_id": "s4-1", "is_from_me": False, "text": "great work on the deck", "created_at": ago(800), "service": "iMessage"},
            {"message_id": "s4-2", "is_from_me": False, "text": "can you send the revised budget before the client call tomorrow? the deadline is tight", "created_at": ago(120), "service": "iMessage"},
        ],
    },
    {
        "thread_id": "seed-5", "contact_name": "Jules", "handles": ["+15550105"],
        "latest_message": "are you free this weekend? thinking we could do that hike finally lol",
        "latest_at": ago(420), "needs_response_estimate": True, "source_type": "imessage",
        "messages": [
            {"message_id": "s5-1", "is_from_me": True, "text": "miss our hangs", "created_at": ago(500), "service": "iMessage"},
            {"message_id": "s5-2", "is_from_me": False, "text": "are you free this weekend? thinking we could do that hike finally lol", "created_at": ago(420), "service": "iMessage"},
        ],
    },
    {
        "thread_id": "seed-6", "contact_name": "Alex", "handles": ["+15550106"],
        "latest_message": "sounds good, talk soon!",
        "latest_at": ago(5980), "needs_response_estimate": False, "source_type": "imessage",
        "messages": [
            {"message_id": "s6-1", "is_from_me": False, "text": "thanks for the recommendation", "created_at": ago(6000), "service": "iMessage"},
            {"message_id": "s6-2", "is_from_me": True, "text": "anytime!", "created_at": ago(5990), "service": "iMessage"},
            {"message_id": "s6-3", "is_from_me": False, "text": "sounds good, talk soon!", "created_at": ago(5980), "service": "iMessage"},
        ],
    },
]


def reset_and_seed():
    init_db()
    db = SessionLocal()
    try:
        # Clear everything for a clean, repeatable seed.
        for model in (Decision, Draft, FollowupItem, ThreadAnalytics, Message,
                      RelationshipSnapshot, Export, TokenUsageEstimate, Thread, Contact):
            db.query(model).delete()
        db.commit()
        count = ingest_threads(db, SEED_THREADS)
        print(f"Seeded {count} synthetic threads.")
    finally:
        db.close()


if __name__ == "__main__":
    reset_and_seed()
