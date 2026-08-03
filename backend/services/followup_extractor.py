import re
from datetime import datetime

PROMISE_PATTERNS = [
    (r"\bi'?ll (send|share|forward|get|check|look|call|text|email|meet|come|bring|handle|fix|update|let you know)\b", "user_owes_them"),
    (r"\bi (will|can|should) (get back|follow up|reach out)\b", "user_owes_them"),
    (r"\bwill do\b", "user_owes_them"),
    (r"\bcount (on|me in)\b", "user_owes_them"),
    (r"\bi'?m on it\b", "user_owes_them"),
    (r"\bsending (it|that|this) (now|soon|today)\b", "user_owes_them"),
]

REQUEST_PATTERNS = [
    (r"\bcan you (send|share|check|look|call|text|get|bring|handle|fix|let me know)\b", "they_owe_user"),
    (r"\bplease (send|share|confirm|let me know|respond|reply|check|get back)\b", "they_owe_user"),
    (r"\bwould you (mind|be able to)\b", "they_owe_user"),
    (r"\bwaiting (for|on) (you|your)\b", "they_owe_user"),
    (r"\bhaven'?t heard (back|from you)\b", "they_owe_user"),
    (r"\bany update\b", "they_owe_user"),
]

SCHEDULING_PATTERNS = [
    (r"\b(are|r) you (free|available)\b", "scheduling_loop"),
    (r"\bwhat (time|day|date) work(s)?\b", "scheduling_loop"),
    (r"\bwhen (can|are|do) you\b", "scheduling_loop"),
    (r"\blet'?s (meet|catch up|grab|get together)\b", "scheduling_loop"),
    (r"\bschedule (a|the) (call|meeting|lunch|dinner|coffee)\b", "scheduling_loop"),
    (r"\bshould we (meet|schedule|plan|set up)\b", "scheduling_loop"),
]

QUESTION_PATTERNS = [
    (r".+\?$", "unanswered_question"),
]

DUE_DATE_PATTERNS = [
    r"\bby (monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    r"\bby (tomorrow|tonight|eod|end of day|end of week|eow)\b",
    r"\bby (january|february|march|april|may|june|july|august|september|october|november|december)\b",
    r"\bby the (\d+)(st|nd|rd|th)\b",
    r"\bdue (on|by|this|next)\b",
    r"\bdeadline\b",
    r"\bthis (week|month|friday|monday|weekend)\b",
    r"\bnext (week|month|friday|monday|weekend)\b",
    r"\btomorrow\b",
    r"\btoday\b",
    r"\basap\b",
    r"\brightaway\b",
]


def _extract_due_date(text: str) -> str | None:
    lower = text.lower()
    for p in DUE_DATE_PATTERNS:
        m = re.search(p, lower)
        if m:
            return m.group(0)
    return None


def _extract_snippet(msg_text: str, pattern: str) -> str:
    m = re.search(pattern, msg_text.lower())
    if m:
        start = max(0, m.start() - 20)
        end = min(len(msg_text), m.end() + 60)
        return msg_text[start:end].strip()
    return msg_text[:100]


def extract_followups(messages: list[dict], thread_id: str) -> list[dict]:
    followups = []
    seen_tasks = set()

    for msg in messages:
        text = msg.get("text", "") or ""
        if not text.strip():
            continue
        is_from_me = msg.get("is_from_me", False)

        for pattern, direction in PROMISE_PATTERNS:
            if is_from_me and re.search(pattern, text.lower()):
                snippet = _extract_snippet(text, pattern)
                key = (direction, snippet[:40].lower())
                if key not in seen_tasks:
                    seen_tasks.add(key)
                    followups.append({
                        "task_text": snippet,
                        "direction": direction,
                        "due_date": _extract_due_date(text),
                        "source_message_id": msg.get("message_id"),
                        "confidence": "medium",
                        "status": "open",
                    })

        for pattern, direction in REQUEST_PATTERNS:
            if not is_from_me and re.search(pattern, text.lower()):
                snippet = _extract_snippet(text, pattern)
                key = (direction, snippet[:40].lower())
                if key not in seen_tasks:
                    seen_tasks.add(key)
                    followups.append({
                        "task_text": snippet,
                        "direction": direction,
                        "due_date": _extract_due_date(text),
                        "source_message_id": msg.get("message_id"),
                        "confidence": "medium",
                        "status": "open",
                    })

        for pattern, direction in SCHEDULING_PATTERNS:
            if re.search(pattern, text.lower()):
                snippet = _extract_snippet(text, pattern)
                key = (direction, snippet[:40].lower())
                if key not in seen_tasks:
                    seen_tasks.add(key)
                    followups.append({
                        "task_text": snippet,
                        "direction": direction,
                        "due_date": _extract_due_date(text),
                        "source_message_id": msg.get("message_id"),
                        "confidence": "low",
                        "status": "open",
                    })

        sentences = [s.strip() for s in re.split(r"[.!]", text) if s.strip()]
        for sentence in sentences:
            if sentence.endswith("?") and not is_from_me:
                key = ("unanswered_question", sentence[:40].lower())
                if key not in seen_tasks:
                    seen_tasks.add(key)
                    followups.append({
                        "task_text": sentence,
                        "direction": "unanswered_question",
                        "due_date": None,
                        "source_message_id": msg.get("message_id"),
                        "confidence": "high",
                        "status": "open",
                    })

    return followups[:20]
