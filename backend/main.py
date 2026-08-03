import json
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.db import get_db, init_db
from backend.models import (
    Contact, Thread, Message, Draft, Decision,
    FollowupItem, ThreadAnalytics, RelationshipSnapshot, Export, TokenUsageEstimate
)
from backend.schemas import DecisionIn, RewriteIn, SettingsIn, DashboardPrefsIn
from backend.config import load_settings, save_settings, load_style_profile
from backend.services.imessage_reader import check_imessage_access, read_threads
from backend.services.ingest import ingest_threads
from backend.services.thread_ranker import rank_thread
from backend.services.draft_generator import generate_draft, rewrite_draft
from backend.services.tone_risk_detector import detect_tone_risks
from backend.services.followup_extractor import extract_followups
from backend.services.relationship_analytics import analyze_thread, build_relationship_snapshot
from backend.services.style_profile import learn_from_decision, get_profile
from backend.services.dashboard_settings import get_or_create_preferences, update_preferences, reset_preferences
from backend.services.token_estimator import get_usage_summary
from backend.services.clipboard_sender import copy_to_clipboard
from backend.services.markdown_exporter import export_daily_digest, export_followups, export_analytics
from backend.services.obsidian_exporter import export_to_obsidian

app = FastAPI(title="ReplyGraph", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    access = check_imessage_access()
    return {"status": "ok", "imessage": access}


# ── iMessage sync ──────────────────────────────────────────────────────────────

@app.post("/sync/imessage")
def sync_imessage(db: Session = Depends(get_db)):
    result = read_threads()
    if not result["ok"]:
        return {"ok": False, "error": result["error"], "synced": 0}

    synced = ingest_threads(db, result["threads"])
    return {"ok": True, "synced": synced, "total_from_source": len(result["threads"])}


# ── Threads ────────────────────────────────────────────────────────────────────

@app.get("/threads")
def list_threads(db: Session = Depends(get_db)):
    threads = db.query(Thread).order_by(Thread.latest_at.desc()).all()
    result = []
    for t in threads:
        contact = db.query(Contact).filter(Contact.id == t.contact_id).first()
        messages = db.query(Message).filter(Message.thread_id == t.id).order_by(Message.created_at).all()
        analytics = db.query(ThreadAnalytics).filter(ThreadAnalytics.thread_id == t.id).order_by(ThreadAnalytics.generated_at.desc()).first()
        result.append({
            "id": t.id,
            "contact_name": contact.display_name if contact else "Unknown",
            "contact_id": t.contact_id,
            "latest_at": t.latest_at.isoformat() if t.latest_at else None,
            "latest_message": t.latest_message,
            "needs_response_estimate": t.needs_response_estimate,
            "priority_label": t.priority_label,
            "urgency": t.urgency,
            "category": t.category,
            "pinned": t.pinned,
            "source_type": t.source_type,
            "message_count": len(messages),
            "analytics": {
                "emotional_tone": analytics.emotional_tone if analytics else None,
                "tone_trend": analytics.tone_trend if analytics else None,
                "confidence": analytics.confidence if analytics else None,
            } if analytics else None,
        })
    return result


@app.get("/threads/{thread_id}")
def get_thread(thread_id: int, db: Session = Depends(get_db)):
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(404, "Thread not found")

    contact = db.query(Contact).filter(Contact.id == thread.contact_id).first()
    messages = db.query(Message).filter(Message.thread_id == thread.id).order_by(Message.created_at).all()
    drafts = db.query(Draft).filter(Draft.thread_id == thread.id).order_by(Draft.created_at.desc()).limit(5).all()
    analytics = db.query(ThreadAnalytics).filter(ThreadAnalytics.thread_id == thread.id).order_by(ThreadAnalytics.generated_at.desc()).first()
    followups = db.query(FollowupItem).filter(FollowupItem.thread_id == thread.id).all()

    return {
        "id": thread.id,
        "contact_name": contact.display_name if contact else "Unknown",
        "contact_id": thread.contact_id,
        "latest_at": thread.latest_at.isoformat() if thread.latest_at else None,
        "latest_message": thread.latest_message,
        "needs_response_estimate": thread.needs_response_estimate,
        "priority_label": thread.priority_label,
        "urgency": thread.urgency,
        "category": thread.category,
        "pinned": thread.pinned,
        "source_type": thread.source_type,
        "messages": [
            {
                "id": m.id,
                "is_from_me": m.is_from_me,
                "text": m.text,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "source_type": m.source_type,
            }
            for m in messages
        ],
        "drafts": [
            {
                "id": d.id,
                "draft_text": d.draft_text,
                "urgency": d.urgency,
                "category": d.category,
                "reason": d.reason,
                "risk_flags": json.loads(d.risk_flags_json or "[]"),
                "confidence": d.confidence,
                "created_at": d.created_at.isoformat(),
            }
            for d in drafts
        ],
        "analytics": {
            "emotional_tone": analytics.emotional_tone,
            "tone_trend": analytics.tone_trend,
            "open_loops": json.loads(analytics.open_loops_json or "[]"),
            "confidence": analytics.confidence,
        } if analytics else None,
        "followups": [
            {
                "id": f.id,
                "task_text": f.task_text,
                "direction": f.direction,
                "due_date": f.due_date,
                "status": f.status,
                "confidence": f.confidence,
            }
            for f in followups
        ],
    }


@app.post("/threads/{thread_id}/draft")
def create_draft(thread_id: int, db: Session = Depends(get_db)):
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(404, "Thread not found")

    contact = db.query(Contact).filter(Contact.id == thread.contact_id).first()
    messages = db.query(Message).filter(Message.thread_id == thread.id).order_by(Message.created_at).all()

    thread_dict = {
        "thread_id": str(thread.id),
        "contact_name": contact.display_name if contact else "Unknown",
        "contact_tone": contact.usual_tone or "unknown" if contact else "unknown",
        "needs_response_estimate": thread.needs_response_estimate,
        "priority_label": thread.priority_label,
        "category": thread.category,
        "messages": [
            {"is_from_me": m.is_from_me, "text": m.text or "", "message_id": str(m.id)}
            for m in messages
        ],
    }

    result = generate_draft(thread_dict)

    draft = Draft(
        thread_id=thread.id,
        draft_text=result.get("draft_reply", ""),
        urgency=result.get("urgency"),
        category=result.get("category"),
        reason=result.get("reason"),
        risk_flags_json=json.dumps(result.get("risk_flags", [])),
        confidence=result.get("confidence"),
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    return {
        "draft_id": draft.id,
        "draft_text": draft.draft_text,
        "urgency": draft.urgency,
        "category": draft.category,
        "reason": draft.reason,
        "risk_flags": json.loads(draft.risk_flags_json or "[]"),
        "confidence": draft.confidence,
        "tone_risks": result.get("tone_risks", {}),
        "mode": result.get("mode", "mock"),
    }


@app.post("/threads/{thread_id}/rewrite")
def rewrite(thread_id: int, body: RewriteIn, db: Session = Depends(get_db)):
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(404, "Thread not found")

    new_text = rewrite_draft(body.draft_text, body.rewrite_type, body.contact_tone)
    tone_risks = detect_tone_risks(new_text)

    return {"draft_text": new_text, "tone_risks": tone_risks}


@app.post("/threads/{thread_id}/approve")
def approve(thread_id: int, body: DecisionIn, db: Session = Depends(get_db)):
    draft = db.query(Draft).filter(Draft.thread_id == thread_id).order_by(Draft.created_at.desc()).first()
    decision = Decision(
        thread_id=thread_id,
        draft_id=draft.id if draft else None,
        decision_type=body.decision_type,
        original_draft=draft.draft_text if draft else None,
        edited_draft=body.edited_draft,
    )
    db.add(decision)
    db.commit()

    learn_from_decision(
        original_draft=draft.draft_text if draft else "",
        edited_draft=body.edited_draft,
        decision_type=body.decision_type,
    )

    return {"ok": True, "decision_type": body.decision_type}


@app.post("/threads/{thread_id}/deny")
def deny(thread_id: int, db: Session = Depends(get_db)):
    draft = db.query(Draft).filter(Draft.thread_id == thread_id).order_by(Draft.created_at.desc()).first()
    decision = Decision(
        thread_id=thread_id,
        draft_id=draft.id if draft else None,
        decision_type="denied",
        original_draft=draft.draft_text if draft else None,
    )
    db.add(decision)
    db.commit()
    learn_from_decision(draft.draft_text if draft else "", None, "denied")
    return {"ok": True}


@app.post("/threads/{thread_id}/no-response")
def no_response(thread_id: int, db: Session = Depends(get_db)):
    db.add(Decision(thread_id=thread_id, decision_type="no_response_needed"))
    db.commit()
    return {"ok": True}


@app.post("/threads/{thread_id}/copy")
def copy_draft(thread_id: int, db: Session = Depends(get_db)):
    draft = db.query(Draft).filter(Draft.thread_id == thread_id).order_by(Draft.created_at.desc()).first()
    if not draft:
        raise HTTPException(404, "No draft found for this thread")

    clipboard_result = copy_to_clipboard(draft.draft_text)

    decision = Decision(
        thread_id=thread_id,
        draft_id=draft.id,
        decision_type="copied",
        original_draft=draft.draft_text,
        copied_to_clipboard=True,
    )
    db.add(decision)
    db.commit()

    return {"ok": True, "clipboard": clipboard_result, "text": draft.draft_text}


@app.post("/threads/{thread_id}/pin")
def pin_thread(thread_id: int, db: Session = Depends(get_db)):
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(404)
    thread.pinned = True
    db.commit()
    return {"ok": True}


@app.post("/threads/{thread_id}/unpin")
def unpin_thread(thread_id: int, db: Session = Depends(get_db)):
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(404)
    thread.pinned = False
    db.commit()
    return {"ok": True}


# ── Contacts ───────────────────────────────────────────────────────────────────

@app.post("/contacts/{contact_id}/pin")
def pin_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(404)
    contact.pinned = True
    db.commit()
    return {"ok": True}


@app.post("/contacts/{contact_id}/unpin")
def unpin_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(404)
    contact.pinned = False
    db.commit()
    return {"ok": True}


# ── Follow-ups ─────────────────────────────────────────────────────────────────

@app.get("/followups")
def list_followups(db: Session = Depends(get_db)):
    items = db.query(FollowupItem).filter(FollowupItem.status == "open").order_by(FollowupItem.created_at.desc()).all()
    result = []
    for f in items:
        contact = db.query(Contact).filter(Contact.id == f.contact_id).first() if f.contact_id else None
        thread = db.query(Thread).filter(Thread.id == f.thread_id).first()
        result.append({
            "id": f.id,
            "task_text": f.task_text,
            "direction": f.direction,
            "due_date": f.due_date,
            "status": f.status,
            "confidence": f.confidence,
            "thread_id": f.thread_id,
            "contact_name": contact.display_name if contact else (thread.latest_message[:20] if thread else "Unknown"),
        })
    return result


@app.post("/followups/{followup_id}/complete")
def complete_followup(followup_id: int, db: Session = Depends(get_db)):
    item = db.query(FollowupItem).filter(FollowupItem.id == followup_id).first()
    if not item:
        raise HTTPException(404)
    item.status = "completed"
    db.commit()
    return {"ok": True}


# ── Analytics ──────────────────────────────────────────────────────────────────

@app.get("/analytics")
def get_analytics(db: Session = Depends(get_db)):
    contacts = db.query(Contact).all()
    result = []
    for contact in contacts:
        threads = db.query(Thread).filter(Thread.contact_id == contact.id).all()
        if not threads:
            continue

        all_messages = []
        for t in threads:
            msgs = db.query(Message).filter(Message.thread_id == t.id).order_by(Message.created_at).all()
            all_messages.extend([
                {"is_from_me": m.is_from_me, "text": m.text or "", "created_at": m.created_at}
                for m in msgs
            ])

        if not all_messages:
            continue

        snapshot = build_relationship_snapshot(contact.display_name, [{"messages": all_messages}])
        snapshot["contact_id"] = contact.id
        snapshot["pinned"] = contact.pinned
        result.append(snapshot)

    return result


@app.post("/analytics/rebuild")
def rebuild_analytics(db: Session = Depends(get_db)):
    db.query(ThreadAnalytics).delete()
    threads = db.query(Thread).all()
    for thread in threads:
        messages = db.query(Message).filter(Message.thread_id == thread.id).order_by(Message.created_at).all()
        msgs_dict = [{"is_from_me": m.is_from_me, "text": m.text or "", "created_at": m.created_at} for m in messages]
        analytics = analyze_thread({"messages": msgs_dict})
        db.add(ThreadAnalytics(
            thread_id=thread.id,
            emotional_tone=analytics["emotional_tone"],
            tone_trend=analytics["tone_trend"],
            response_status=analytics["response_status"],
            open_loops_json=json.dumps(analytics["open_loops"]),
            confidence=analytics["confidence"],
        ))
    db.commit()
    return {"ok": True, "rebuilt": len(threads)}


# ── Style profile ──────────────────────────────────────────────────────────────

@app.get("/style-profile")
def get_style_profile():
    return get_profile()


@app.post("/style-profile/update")
def update_style_profile(body: dict):
    from backend.config import save_style_profile
    profile = get_profile()
    profile.update(body)
    save_style_profile(profile)
    return profile


# ── Dashboard preferences ──────────────────────────────────────────────────────

@app.get("/dashboard/preferences")
def get_dashboard_prefs():
    return get_or_create_preferences()


@app.post("/dashboard/preferences")
def set_dashboard_prefs(body: DashboardPrefsIn):
    return update_preferences(body.data)


@app.post("/dashboard/preferences/reset")
def reset_dashboard_prefs():
    return reset_preferences()


# ── Exports ────────────────────────────────────────────────────────────────────

@app.get("/exports")
def list_exports(db: Session = Depends(get_db)):
    exports = db.query(Export).order_by(Export.created_at.desc()).limit(20).all()
    return [{"id": e.id, "type": e.export_type, "path": e.file_path, "created_at": e.created_at.isoformat()} for e in exports]


@app.post("/exports/markdown")
def export_markdown(db: Session = Depends(get_db)):
    threads = db.query(Thread).order_by(Thread.latest_at.desc()).all()
    threads_data = []
    for t in threads:
        contact = db.query(Contact).filter(Contact.id == t.contact_id).first()
        threads_data.append({
            "contact_name": contact.display_name if contact else "Unknown",
            "latest_message": t.latest_message,
            "needs_response_estimate": t.needs_response_estimate,
            "priority_label": t.priority_label,
            "urgency": t.urgency,
        })

    followups = db.query(FollowupItem).filter(FollowupItem.status == "open").all()
    followups_data = [{"task_text": f.task_text, "direction": f.direction, "due_date": f.due_date, "confidence": f.confidence} for f in followups]

    analytics_rows = db.query(ThreadAnalytics).all()
    analytics_data = []
    for a in analytics_rows:
        thread = db.query(Thread).filter(Thread.id == a.thread_id).first()
        contact = db.query(Contact).filter(Contact.id == thread.contact_id).first() if thread else None
        analytics_data.append({
            "contact_name": contact.display_name if contact else "Unknown",
            "emotional_tone": a.emotional_tone,
            "tone_trend": a.tone_trend,
            "confidence": a.confidence,
            "message_volume": 0,
            "common_topics": [],
        })

    digest_path = export_daily_digest(threads_data)
    followups_path = export_followups(followups_data)
    analytics_path = export_analytics(analytics_data)

    for path, etype in [(digest_path, "daily_digest"), (followups_path, "followups"), (analytics_path, "analytics")]:
        db.add(Export(export_type=etype, file_path=str(path)))
    db.commit()

    return {
        "ok": True,
        "files": [str(digest_path), str(followups_path), str(analytics_path)],
    }


@app.post("/exports/obsidian")
def export_obsidian_route(db: Session = Depends(get_db)):
    threads = db.query(Thread).order_by(Thread.latest_at.desc()).all()
    threads_data = []
    for t in threads:
        contact = db.query(Contact).filter(Contact.id == t.contact_id).first()
        threads_data.append({
            "contact_name": contact.display_name if contact else "Unknown",
            "latest_message": t.latest_message,
            "needs_response_estimate": t.needs_response_estimate,
            "priority_label": t.priority_label,
        })

    followups = db.query(FollowupItem).filter(FollowupItem.status == "open").all()
    followups_data = [{"task_text": f.task_text, "direction": f.direction, "due_date": f.due_date, "confidence": f.confidence} for f in followups]

    analytics_rows = db.query(ThreadAnalytics).all()
    analytics_data = []
    for a in analytics_rows:
        thread = db.query(Thread).filter(Thread.id == a.thread_id).first()
        contact = db.query(Contact).filter(Contact.id == thread.contact_id).first() if thread else None
        analytics_data.append({
            "contact_name": contact.display_name if contact else "Unknown",
            "emotional_tone": a.emotional_tone,
            "confidence": a.confidence,
        })

    result = export_to_obsidian(threads_data, followups_data, analytics_data)
    if result["ok"]:
        db.add(Export(export_type="obsidian", file_path=str(result.get("files_written", []))))
        db.commit()
    return result


# ── Settings ───────────────────────────────────────────────────────────────────

@app.get("/settings")
def get_settings():
    settings = load_settings()
    safe = {k: v for k, v in settings.items() if k != "llm_api_key"}
    safe["llm_api_key_set"] = bool(settings.get("llm_api_key"))
    safe["imessage_status"] = check_imessage_access()
    return safe


@app.post("/settings")
def update_settings(body: SettingsIn):
    settings = load_settings()
    settings.update(body.data)
    save_settings(settings)
    return {"ok": True}


@app.get("/token-usage")
def token_usage():
    return get_usage_summary()
