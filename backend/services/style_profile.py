import json
from datetime import datetime
from backend.config import load_style_profile, save_style_profile, STYLE_PROFILE_PATH


def get_profile() -> dict:
    return load_style_profile()


def _snapshot(profile: dict, trigger: str):
    from backend.db import SessionLocal
    from backend.models import StyleProfileSnapshot
    db = SessionLocal()
    try:
        snap = StyleProfileSnapshot(
            profile_json=json.dumps(profile),
            trigger_event=trigger,
        )
        db.add(snap)
        db.commit()
    finally:
        db.close()


def learn_from_decision(original_draft: str, edited_draft: str | None, decision_type: str):
    profile = load_style_profile()
    prefs = profile.setdefault("learned_preferences", {})

    if decision_type == "denied":
        return

    if edited_draft and original_draft:
        orig_words = len(original_draft.split())
        edit_words = len(edited_draft.split())
        ratio = edit_words / orig_words if orig_words else 1

        length_history = prefs.setdefault("length_ratios", [])
        length_history.append(round(ratio, 2))
        if len(length_history) > 20:
            length_history.pop(0)

        avg = sum(length_history) / len(length_history)
        if avg < 0.7:
            prefs["preferred_length"] = "short"
        elif avg > 1.2:
            prefs["preferred_length"] = "long"
        else:
            prefs["preferred_length"] = "medium"

        orig_lower = original_draft.lower()
        edit_lower = edited_draft.lower()
        apology_words = ["sorry", "apologize", "my fault", "my bad"]
        removed_apologies = sum(1 for w in apology_words if w in orig_lower and w not in edit_lower)
        if removed_apologies > 0:
            apology_count = prefs.get("removed_apologies", 0) + removed_apologies
            prefs["removed_apologies"] = apology_count
            if apology_count >= 3:
                prefs["apology_frequency"] = "low"

        edit_history = profile.setdefault("edit_history_summary", [])
        edit_history.append({
            "decision": decision_type,
            "original_word_count": orig_words,
            "edited_word_count": edit_words,
            "at": datetime.utcnow().isoformat(),
        })
        if len(edit_history) > 50:
            edit_history.pop(0)

    save_style_profile(profile)
    _snapshot(profile, trigger=decision_type)


def build_style_instructions(profile: dict, tone: str = "unknown") -> str:
    rules = profile.get("global_rules", [])
    tones = profile.get("tones", {})
    avoid = profile.get("avoid", [])
    prefs = profile.get("learned_preferences", {})

    tone_desc = tones.get(tone, tones.get("unknown", "neutral, polite, concise"))
    length_pref = prefs.get("preferred_length", "medium")
    apology_pref = prefs.get("apology_frequency", "normal")

    parts = [
        f"Style rules: {', '.join(rules)}.",
        f"Tone for this contact: {tone_desc}.",
        f"Preferred reply length: {length_pref}.",
    ]
    if apology_pref == "low":
        parts.append("Avoid apologizing unless strictly necessary.")
    if avoid:
        parts.append(f"Avoid: {', '.join(avoid)}.")

    return " ".join(parts)
