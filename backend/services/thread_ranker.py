import re
from datetime import datetime, timezone

URGENCY_WORDS = [
    r"\basap\b", r"\burgent\b", r"\bimmediately\b", r"\bright now\b",
    r"\btoday\b", r"\bdeadline\b", r"\bdue\b", r"\boverdue\b", r"\blast chance\b",
]
QUESTION_PATTERN = re.compile(r"\?")
SCHEDULE_WORDS = [
    r"\bmeet\b", r"\bmeeting\b", r"\bcall\b", r"\blunch\b", r"\bdinne?r\b",
    r"\bcoffee\b", r"\bschedule\b", r"\bavailable\b", r"\bfree\b", r"\btime\b",
    r"\bwhen\b", r"\bweekend\b",
]
EMOTIONAL_WORDS = [
    r"\blove\b", r"\bmiss\b", r"\bsorry\b", r"\bhurt\b", r"\bangry\b", r"\bsad\b",
    r"\bupset\b", r"\bworried\b", r"\bscared\b", r"\bhappy\b", r"\bexcited\b",
    r"\bthank\b", r"\bappreciat\b", r"\bcare\b",
]
WORK_WORDS = [
    r"\bproject\b", r"\bclient\b", r"\breport\b", r"\bboss\b", r"\bmanager\b",
    r"\bteam\b", r"\boffice\b", r"\bwork\b", r"\bjob\b", r"\bcontract\b",
    r"\bpresentation\b", r"\bbudget\b",
]
RISK_WORDS = [
    r"\bdoctor\b", r"\bhospital\b", r"\bmedical\b", r"\bmoney\b", r"\bpay\b",
    r"\blawyer\b", r"\blegal\b", r"\bcourt\b", r"\bfight\b", r"\bargue\b",
    r"\bconflict\b", r"\bdivorc\b", r"\bsue\b",
]


def _matches(text: str, patterns: list[str]) -> int:
    count = 0
    lower = text.lower()
    for p in patterns:
        if re.search(p, lower):
            count += 1
    return count


def _days_since(dt: datetime | None) -> float:
    if dt is None:
        return 999
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if dt.tzinfo is not None:
        now = datetime.now(timezone.utc)
    return max(0, (now - dt).total_seconds() / 86400)


def rank_thread(thread: dict) -> dict:
    messages = thread.get("messages", [])
    latest_at = thread.get("latest_at")
    needs_response = thread.get("needs_response_estimate", False)

    recent_inbound = [m for m in messages[-5:] if not m.get("is_from_me")]
    all_inbound_text = " ".join(m.get("text", "") for m in recent_inbound)
    full_text = " ".join(m.get("text", "") for m in messages[-10:])

    urgency_score = _matches(full_text, URGENCY_WORDS)
    question_score = len(QUESTION_PATTERN.findall(full_text))
    sched_score = _matches(full_text, SCHEDULE_WORDS)
    emotional_score = _matches(full_text, EMOTIONAL_WORDS)
    work_score = _matches(full_text, WORK_WORDS)
    risk_score = _matches(full_text, RISK_WORDS)
    days_old = _days_since(latest_at)
    repeated_inbound = len(recent_inbound) >= 3

    if not needs_response:
        label = "no_response_needed"
        urgency = "low"
        category = "no_reply_needed"
    elif risk_score >= 2:
        label = "risky_to_answer_fast"
        urgency = "high"
        category = "review_carefully"
    elif urgency_score >= 2 or (days_old > 3 and repeated_inbound):
        label = "urgent"
        urgency = "high"
        category = "reply_needed"
    elif emotional_score >= 2:
        label = "emotional"
        urgency = "medium"
        category = "emotional"
    elif sched_score >= 2 or (question_score >= 1 and sched_score >= 1):
        label = "logistical"
        urgency = "medium"
        category = "scheduling"
    elif work_score >= 2:
        label = "work_admin"
        urgency = "medium"
        category = "work"
    elif question_score >= 1:
        label = "logistical"
        urgency = "medium"
        category = "question"
    elif days_old > 7:
        label = "low_priority"
        urgency = "low"
        category = "reply_needed"
    else:
        label = "low_priority"
        urgency = "low"
        category = "reply_needed"

    return {
        **thread,
        "priority_label": label,
        "urgency": urgency,
        "category": category,
        "risk_score": risk_score,
    }
