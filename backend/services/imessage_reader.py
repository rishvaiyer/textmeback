import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.config import get_imessage_db_path, load_settings


APPLE_EPOCH_OFFSET = 978307200  # seconds between Unix epoch and Apple epoch (Jan 1 2001)


def _apple_ts_to_datetime(ts: int | None) -> datetime | None:
    if ts is None:
        return None
    try:
        unix_ts = (ts / 1e9) + APPLE_EPOCH_OFFSET
        return datetime.fromtimestamp(unix_ts, tz=timezone.utc).replace(tzinfo=None)
    except Exception:
        return None


def _open_readonly(db_path: Path) -> sqlite3.Connection:
    uri = f"file:{db_path}?mode=ro"
    return sqlite3.connect(uri, uri=True, check_same_thread=False)


def check_imessage_access() -> dict:
    db_path = get_imessage_db_path()
    if not db_path.exists():
        return {
            "accessible": False,
            "path": str(db_path),
            "error": (
                "chat.db not found. On macOS go to System Settings → Privacy & Security → "
                "Full Disk Access and grant access to Terminal (or your app). "
                f"Expected path: {db_path}"
            ),
        }
    try:
        conn = _open_readonly(db_path)
        conn.execute("SELECT count(*) FROM message LIMIT 1")
        conn.close()
        return {"accessible": True, "path": str(db_path), "error": None}
    except sqlite3.OperationalError as e:
        msg = str(e)
        if "unable to open" in msg or "permission" in msg.lower():
            return {
                "accessible": False,
                "path": str(db_path),
                "error": (
                    "Permission denied reading chat.db. Grant Full Disk Access in "
                    "System Settings → Privacy & Security → Full Disk Access."
                ),
            }
        return {"accessible": False, "path": str(db_path), "error": f"Database error: {msg}"}
    except Exception as e:
        return {"accessible": False, "path": str(db_path), "error": f"Unexpected error: {e}"}


def _get_contact_name(conn: sqlite3.Connection, handle_id: int) -> tuple[str, str]:
    row = conn.execute(
        "SELECT id FROM handle WHERE ROWID = ?", (handle_id,)
    ).fetchone()
    handle = row[0] if row else "Unknown"
    return handle, handle


def read_threads() -> dict:
    access = check_imessage_access()
    if not access["accessible"]:
        return {"ok": False, "error": access["error"], "threads": []}

    settings = load_settings()
    max_threads = settings.get("max_threads", 50)
    max_messages = settings.get("max_messages_per_thread", 50)

    db_path = get_imessage_db_path()
    try:
        conn = _open_readonly(db_path)
        conn.row_factory = sqlite3.Row

        chat_rows = conn.execute(
            """
            SELECT
                c.ROWID          AS chat_rowid,
                c.chat_identifier,
                c.display_name,
                MAX(m.date)      AS latest_date
            FROM chat c
            JOIN chat_message_join cmj ON cmj.chat_id = c.ROWID
            JOIN message m            ON m.ROWID = cmj.message_id
            WHERE m.text IS NOT NULL AND m.text != ''
            GROUP BY c.ROWID
            ORDER BY latest_date DESC
            LIMIT ?
            """,
            (max_threads,),
        ).fetchall()

        threads = []
        for chat in chat_rows:
            chat_id = chat["chat_rowid"]
            identifier = chat["chat_identifier"] or ""
            display = chat["display_name"] or identifier

            handle_rows = conn.execute(
                """
                SELECT h.id FROM handle h
                JOIN chat_handle_join chj ON chj.handle_id = h.ROWID
                WHERE chj.chat_id = ?
                """,
                (chat_id,),
            ).fetchall()
            handles = [r["id"] for r in handle_rows]
            if not handles:
                handles = [identifier]

            msg_rows = conn.execute(
                """
                SELECT
                    m.ROWID          AS message_rowid,
                    m.is_from_me,
                    m.text,
                    m.date,
                    m.service
                FROM message m
                JOIN chat_message_join cmj ON cmj.message_id = m.ROWID
                WHERE cmj.chat_id = ? AND m.text IS NOT NULL AND m.text != ''
                ORDER BY m.date DESC
                LIMIT ?
                """,
                (chat_id, max_messages),
            ).fetchall()

            messages = []
            for msg in reversed(msg_rows):
                messages.append(
                    {
                        "message_id": str(msg["message_rowid"]),
                        "is_from_me": bool(msg["is_from_me"]),
                        "text": msg["text"] or "",
                        "created_at": _apple_ts_to_datetime(msg["date"]),
                        "service": msg["service"] or "iMessage",
                    }
                )

            latest_at = _apple_ts_to_datetime(chat["latest_date"])
            latest_text = messages[-1]["text"] if messages else ""

            needs_response = _estimate_needs_response(messages)

            threads.append(
                {
                    "thread_id": str(chat_id),
                    "contact_name": display,
                    "handles": handles,
                    "latest_message": latest_text,
                    "latest_at": latest_at,
                    "needs_response_estimate": needs_response,
                    "messages": messages,
                }
            )

        conn.close()
        return {"ok": True, "error": None, "threads": threads}

    except sqlite3.OperationalError as e:
        return {
            "ok": False,
            "error": f"Query failed: {e}. The Messages database schema may differ from expected.",
            "threads": [],
        }
    except Exception as e:
        return {"ok": False, "error": f"Unexpected error reading iMessage: {e}", "threads": []}


def _estimate_needs_response(messages: list[dict]) -> bool:
    if not messages:
        return False
    last = messages[-1]
    if last["is_from_me"]:
        return False
    inbound_streak = 0
    for msg in reversed(messages):
        if not msg["is_from_me"]:
            inbound_streak += 1
        else:
            break
    return inbound_streak >= 1
