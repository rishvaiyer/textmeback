from datetime import datetime
from pathlib import Path
from backend.config import get_export_folder


def _now_str() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")


def export_daily_digest(threads: list[dict]) -> Path:
    folder = get_export_folder()
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    path = folder / f"daily_digest_{date_str}.md"

    needs_reply = [t for t in threads if t.get("needs_response_estimate")]
    high_risk = [t for t in threads if t.get("priority_label") == "risky_to_answer_fast"]

    lines = [
        f"# Daily Communication Digest — {date_str}",
        f"_Generated: {_now_str()}_",
        "",
        f"## Summary",
        f"- Threads reviewed: {len(threads)}",
        f"- Needs reply: {len(needs_reply)}",
        f"- High risk: {len(high_risk)}",
        "",
        "## Needs Reply",
    ]

    for t in needs_reply[:20]:
        contact = t.get("contact_name", "Unknown")
        latest = (t.get("latest_message") or "")[:120]
        priority = t.get("priority_label", "")
        lines.append(f"- **{contact}** [{priority}]: {latest}")

    lines += ["", "## High Risk Threads"]
    for t in high_risk:
        contact = t.get("contact_name", "Unknown")
        latest = (t.get("latest_message") or "")[:120]
        lines.append(f"- **{contact}**: {latest}")

    path.write_text("\n".join(lines))
    return path


def export_followups(followups: list[dict]) -> Path:
    folder = get_export_folder()
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    path = folder / f"followups_{date_str}.md"

    lines = [
        f"# Follow-ups — {date_str}",
        f"_Generated: {_now_str()}_",
        "",
    ]

    by_direction = {}
    for f in followups:
        d = f.get("direction", "unknown")
        by_direction.setdefault(d, []).append(f)

    direction_labels = {
        "user_owes_them": "I Owe Them",
        "they_owe_user": "They Owe Me",
        "scheduling_loop": "Scheduling Loops",
        "unanswered_question": "Unanswered Questions",
    }

    for direction, label in direction_labels.items():
        items = by_direction.get(direction, [])
        if not items:
            continue
        lines.append(f"## {label}")
        for item in items:
            task = item.get("task_text", "")[:120]
            due = item.get("due_date", "")
            conf = item.get("confidence", "")
            due_str = f" (due: {due})" if due else ""
            lines.append(f"- [ ] {task}{due_str} _{conf} confidence_")
        lines.append("")

    path.write_text("\n".join(lines))
    return path


def export_analytics(analytics_data: list[dict]) -> Path:
    folder = get_export_folder()
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    path = folder / f"analytics_{date_str}.md"

    lines = [
        f"# Relationship Analytics — {date_str}",
        f"_Generated: {_now_str()}_",
        "_Confidence labels are estimates, not facts._",
        "",
    ]

    for a in analytics_data:
        name = a.get("contact_name", "Unknown")
        tone = a.get("emotional_tone", "unknown")
        trend = a.get("tone_trend", "stable")
        topics = ", ".join(a.get("common_topics", [])) or "none detected"
        conf = a.get("confidence", "low")
        vol = a.get("message_volume", 0)
        lines += [
            f"### {name}",
            f"- Message volume: {vol}",
            f"- This thread appears **{tone}** lately (trend: {trend}) _{conf} confidence_",
            f"- Common topics: {topics}",
            "",
        ]

    path.write_text("\n".join(lines))
    return path
