import json
from sqlalchemy.orm import Session

from backend.models import Contact, Thread, Message, FollowupItem, ThreadAnalytics
from backend.services.thread_ranker import rank_thread
from backend.services.followup_extractor import extract_followups
from backend.services.relationship_analytics import analyze_thread


def ingest_threads(db: Session, raw_threads: list[dict]) -> int:
    """Upsert normalized thread objects into the DB and (re)compute
    ranking, follow-ups and per-thread analytics.

    Shared by the live iMessage sync endpoint and the dev seed so both
    take exactly the same code path.
    """
    synced = 0
    for raw_thread in raw_threads:
        ext_id = raw_thread["thread_id"]
        ranked = rank_thread(raw_thread)

        contact_handle = raw_thread["handles"][0] if raw_thread.get("handles") else "unknown"
        contact_name = raw_thread["contact_name"]

        contact = db.query(Contact).filter(Contact.handle == contact_handle).first()
        if not contact:
            contact = Contact(display_name=contact_name, handle=contact_handle)
            db.add(contact)
            db.flush()

        thread = db.query(Thread).filter(Thread.external_thread_id == ext_id).first()
        if not thread:
            thread = Thread(
                external_thread_id=ext_id,
                source_type=raw_thread.get("source_type", "imessage"),
                contact_id=contact.id,
            )
            db.add(thread)
            db.flush()

        thread.latest_at = raw_thread.get("latest_at")
        thread.latest_message = (raw_thread.get("latest_message") or "")[:500]
        thread.needs_response_estimate = ranked.get("needs_response_estimate", False)
        thread.priority_label = ranked.get("priority_label")
        thread.urgency = ranked.get("urgency")
        thread.category = ranked.get("category")
        contact.display_name = contact_name

        existing_msg_ids = {
            m.external_message_id
            for m in db.query(Message.external_message_id).filter(Message.thread_id == thread.id).all()
        }
        for msg in raw_thread.get("messages", []):
            mid = msg["message_id"]
            if mid not in existing_msg_ids:
                db.add(Message(
                    thread_id=thread.id,
                    external_message_id=mid,
                    is_from_me=msg["is_from_me"],
                    text=msg["text"],
                    created_at=msg["created_at"],
                    source_type=raw_thread.get("source_type", "imessage"),
                ))

        followups = extract_followups(raw_thread.get("messages", []), ext_id)
        db.query(FollowupItem).filter(FollowupItem.thread_id == thread.id).delete()
        for f in followups:
            db.add(FollowupItem(
                thread_id=thread.id,
                contact_id=contact.id if contact else None,
                task_text=f["task_text"],
                direction=f["direction"],
                due_date=f["due_date"],
                confidence=f["confidence"],
                status=f["status"],
            ))

        analytics = analyze_thread(raw_thread)
        db.query(ThreadAnalytics).filter(ThreadAnalytics.thread_id == thread.id).delete()
        db.add(ThreadAnalytics(
            thread_id=thread.id,
            emotional_tone=analytics["emotional_tone"],
            tone_trend=analytics["tone_trend"],
            response_status=analytics["response_status"],
            open_loops_json=json.dumps(analytics["open_loops"]),
            confidence=analytics["confidence"],
        ))

        synced += 1

    db.commit()
    return synced
