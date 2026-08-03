import re
from datetime import datetime, timezone
from collections import Counter

TONE_SIGNALS = {
    "warm": [r"\blove\b", r"\bmiss you\b", r"\bso good\b", r"\bcan'?t wait\b", r"\bthank you\b", r"\bappreciat\b", r"\bcare\b", r"\bso happy\b"],
    "playful": [r"\blol\b", r"\bhaha\b", r"\b😂\b", r"\b😅\b", r"\b🤣\b", r"\bjoke\b", r"\bfunny\b", r"\bwait what\b"],
    "tense": [r"\bseriously\b", r"\bfrustrat\b", r"\bannoy\b", r"\bupset\b", r"\bagain\b.*\bthis\b", r"\bwhy (do|did|would) you\b"],
    "supportive": [r"\bhere for you\b", r"\blet me know\b.*\bhelp\b", r"\byou got this\b", r"\bproud of\b", r"\byou'?re doing\b"],
    "logistical": [r"\bplan\b", r"\bschedule\b", r"\bconfirm\b", r"\btime\b", r"\baddress\b", r"\bdetails\b", r"\binfo\b"],
    "distant": [r"^(k|ok|okay|sure|fine|noted|yep|yup|np)\.*$"],
    "conflict_risk": [r"\bfight\b", r"\bargue\b", r"\bcan'?t believe\b", r"\byou always\b", r"\byou never\b", r"\bstop (doing|saying|being)\b"],
}

TOPIC_SIGNALS = {
    "work": [r"\bwork\b", r"\bjob\b", r"\bproject\b", r"\bclient\b", r"\bmeeting\b", r"\boffice\b"],
    "family": [r"\bmom\b", r"\bdad\b", r"\bsister\b", r"\bbrother\b", r"\bkids?\b", r"\bfamily\b", r"\bparents?\b"],
    "health": [r"\bdoctor\b", r"\bhospital\b", r"\bsick\b", r"\btherapy\b", r"\bpain\b", r"\bfeel (better|worse)\b"],
    "money": [r"\bpay\b", r"\brent\b", r"\bbill\b", r"\bmoney\b", r"\bcost\b", r"\bafford\b"],
    "plans": [r"\bplan\b", r"\bweekend\b", r"\btrip\b", r"\bvacation\b", r"\bvisit\b", r"\bcoming\b"],
    "food": [r"\bdinner\b", r"\blunch\b", r"\brestaurant\b", r"\bcook\b", r"\beat\b", r"\bfood\b"],
}


def _score_text(text: str, signal_dict: dict) -> Counter:
    lower = text.lower()
    scores = Counter()
    for label, patterns in signal_dict.items():
        for p in patterns:
            if re.search(p, lower):
                scores[label] += 1
    return scores


def _days_since(dt: datetime | None) -> float:
    if dt is None:
        return 999
    now = datetime.utcnow()
    return max(0.0, (now - dt).total_seconds() / 86400)


def _avg_response_hours(messages: list[dict]) -> float | None:
    pairs = []
    for i in range(1, len(messages)):
        prev = messages[i - 1]
        curr = messages[i]
        if prev.get("is_from_me") != curr.get("is_from_me"):
            t_prev = prev.get("created_at")
            t_curr = curr.get("created_at")
            if t_prev and t_curr:
                delta = (t_curr - t_prev).total_seconds() / 3600
                if 0 < delta < 168:
                    pairs.append(delta)
    if not pairs:
        return None
    return round(sum(pairs) / len(pairs), 1)


def analyze_thread(thread: dict) -> dict:
    messages = thread.get("messages", [])
    if not messages:
        return {
            "emotional_tone": "neutral",
            "tone_trend": "stable",
            "response_status": "unknown",
            "open_loops": [],
            "confidence": "low",
            "message_volume": 0,
            "last_interaction_days": 999,
            "avg_response_hours": None,
            "common_topics": [],
        }

    all_text = " ".join(m.get("text", "") for m in messages)
    recent_text = " ".join(m.get("text", "") for m in messages[-5:])
    older_text = " ".join(m.get("text", "") for m in messages[:-5]) if len(messages) > 5 else all_text

    tone_scores_all = _score_text(all_text, TONE_SIGNALS)
    tone_scores_recent = _score_text(recent_text, TONE_SIGNALS)
    tone_scores_older = _score_text(older_text, TONE_SIGNALS)
    topic_scores = _score_text(all_text, TOPIC_SIGNALS)

    dominant_tone = tone_scores_all.most_common(1)[0][0] if tone_scores_all else "neutral"

    recent_top = tone_scores_recent.most_common(1)[0][0] if tone_scores_recent else None
    older_top = tone_scores_older.most_common(1)[0][0] if tone_scores_older else None

    if recent_top == older_top or not recent_top or not older_top:
        tone_trend = "stable"
    elif recent_top in ("tense", "conflict_risk", "distant") and older_top in ("warm", "playful", "supportive"):
        tone_trend = "declining"
    elif recent_top in ("warm", "playful", "supportive") and older_top in ("tense", "conflict_risk", "distant"):
        tone_trend = "improving"
    else:
        tone_trend = "shifting"

    inbound = [m for m in messages if not m.get("is_from_me")]
    outbound = [m for m in messages if m.get("is_from_me")]
    last_is_inbound = messages[-1] and not messages[-1].get("is_from_me")

    response_status = "caught_up"
    if last_is_inbound:
        response_status = "awaiting_your_reply"
    elif outbound and not inbound:
        response_status = "awaiting_their_reply"

    open_loops = []
    for m in messages[-10:]:
        text = m.get("text", "") or ""
        if "?" in text and not m.get("is_from_me"):
            open_loops.append(text[:80])

    common_topics = [t for t, _ in topic_scores.most_common(3)]

    total = len(messages)
    confidence = "high" if total >= 10 else "medium" if total >= 4 else "low"

    last_dt = messages[-1].get("created_at") if messages else None
    last_interaction_days = round(_days_since(last_dt), 1)

    return {
        "emotional_tone": dominant_tone,
        "tone_trend": tone_trend,
        "response_status": response_status,
        "open_loops": open_loops[:5],
        "confidence": confidence,
        "message_volume": total,
        "last_interaction_days": last_interaction_days,
        "avg_response_hours": _avg_response_hours(messages),
        "common_topics": common_topics,
        "user_waiting_on_them": 1 if response_status == "awaiting_their_reply" else 0,
        "they_waiting_on_user": 1 if response_status == "awaiting_your_reply" else 0,
    }


def build_relationship_snapshot(contact_name: str, threads_for_contact: list[dict]) -> dict:
    all_messages = []
    for t in threads_for_contact:
        all_messages.extend(t.get("messages", []))

    all_messages.sort(key=lambda m: m.get("created_at") or datetime.min)

    if not all_messages:
        return {
            "contact_name": contact_name,
            "message_volume": 0,
            "last_interaction": None,
            "avg_response_hours": None,
            "emotional_tone": "unknown",
            "tone_trend": "unknown",
            "common_topics": [],
            "open_loops": [],
            "confidence": "low",
        }

    last_dt = all_messages[-1].get("created_at")
    analysis = analyze_thread({"messages": all_messages})

    return {
        "contact_name": contact_name,
        "message_volume": analysis["message_volume"],
        "last_interaction": last_dt.isoformat() if last_dt else None,
        "avg_response_hours": analysis["avg_response_hours"],
        "emotional_tone": analysis["emotional_tone"],
        "tone_trend": analysis["tone_trend"],
        "common_topics": analysis["common_topics"],
        "open_loops": analysis["open_loops"],
        "confidence": analysis["confidence"],
        "user_waiting_on_them": analysis["user_waiting_on_them"],
        "they_waiting_on_user": analysis["they_waiting_on_user"],
    }
