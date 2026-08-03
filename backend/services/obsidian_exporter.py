from datetime import datetime
from pathlib import Path
from backend.config import load_settings


def _frontmatter(export_type: str, confidence: str = "medium") -> str:
    return f"""---
source: replygraph
generated_at: {datetime.utcnow().strftime("%Y-%m-%d")}
export_type: {export_type}
confidence: {confidence}
---

"""


def _get_vault_root() -> Path | None:
    settings = load_settings()
    vault = settings.get("obsidian_vault_path", "").strip()
    if not vault:
        return None
    p = Path(vault).expanduser()
    if not p.exists():
        return None
    return p


def export_to_obsidian(threads: list[dict], followups: list[dict], analytics: list[dict]) -> dict:
    vault = _get_vault_root()
    if not vault:
        return {"ok": False, "error": "Obsidian vault path not configured or not found in settings."}

    rg_root = vault / "ReplyGraph"
    daily_dir = rg_root / "Daily"
    contacts_dir = rg_root / "Contacts"
    followups_dir = rg_root / "Followups"
    analytics_dir = rg_root / "Analytics"

    for d in [daily_dir, contacts_dir, followups_dir, analytics_dir]:
        d.mkdir(parents=True, exist_ok=True)

    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    written = []

    # Daily digest
    daily_path = daily_dir / f"{date_str}.md"
    needs_reply = [t for t in threads if t.get("needs_response_estimate")]
    lines = [
        _frontmatter("daily_digest"),
        f"# Daily Digest — {date_str}",
        "",
        f"- Total threads: {len(threads)}",
        f"- Needs reply: {len(needs_reply)}",
        "",
        "## Needs Reply",
    ]
    for t in needs_reply[:15]:
        contact = t.get("contact_name", "Unknown")
        msg = (t.get("latest_message") or "")[:100]
        lines.append(f"- [[{contact}]]: {msg}")
    lines += ["", "See [[Followups]] and [[Communication Analytics]]."]
    daily_path.write_text("\n".join(lines))
    written.append(str(daily_path))

    # Contact pages
    contact_map: dict[str, list] = {}
    for t in threads:
        name = t.get("contact_name", "Unknown")
        contact_map.setdefault(name, []).append(t)

    for name, contact_threads in contact_map.items():
        safe_name = name.replace("/", "_").replace("\\", "_")
        contact_path = contacts_dir / f"{safe_name}.md"
        last_msg = contact_threads[0].get("latest_message", "")[:100] if contact_threads else ""
        lines = [
            _frontmatter("contact_summary"),
            f"# {name}",
            "",
            f"Threads: {len(contact_threads)}",
            f"Last message: {last_msg}",
            "",
            "## [[Followups]]",
            "## [[Communication Analytics]]",
        ]
        contact_path.write_text("\n".join(lines))
        written.append(str(contact_path))

    # Followups
    followups_path = followups_dir / f"{date_str}.md"
    lines = [_frontmatter("followups"), "# Follow-ups", ""]
    for f in followups:
        task = (f.get("task_text") or "")[:120]
        direction = f.get("direction", "")
        due = f.get("due_date", "")
        due_str = f" — due: {due}" if due else ""
        lines.append(f"- [ ] [{direction}] {task}{due_str}")
    followups_path.write_text("\n".join(lines))
    written.append(str(followups_path))

    # Analytics
    analytics_path = analytics_dir / f"{date_str}.md"
    lines = [
        _frontmatter("analytics"),
        "# Communication Analytics",
        "_Tone labels are estimates, not facts._",
        "",
    ]
    for a in analytics:
        name = a.get("contact_name", "Unknown")
        tone = a.get("emotional_tone", "unknown")
        conf = a.get("confidence", "low")
        lines.append(f"- [[{name}]]: appears **{tone}** _{conf} confidence_")
    analytics_path.write_text("\n".join(lines))
    written.append(str(analytics_path))

    return {"ok": True, "files_written": written}
