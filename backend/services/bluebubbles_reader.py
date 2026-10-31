"""Read conversations from a BlueBubbles server, so TextMeBack runs on Linux and other devices.

iMessage only exists on Apple hardware. BlueBubbles is an open-source server that runs on a Mac and
serves its messages over HTTP. This reader asks that server for the same normalized threads the local
chat.db reader produces, so nothing downstream changes. It is read-only: it never calls a send endpoint.

Status: written against the BlueBubbles REST API (password passed as the `guid` query parameter).
Exercised against a stand-in server in tests, not yet against a live BlueBubbles install.
"""
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

from backend.services.imessage_reader import _estimate_needs_response

TIMEOUT = 15.0


def normalize_base_url(raw: str) -> str:
    """Accept what people paste ("192.168.1.20:1234", "https://x.ngrok.io/") and return a clean base URL."""
    value = (raw or "").strip()
    if not value:
        raise ValueError("Enter the address of your BlueBubbles server.")
    if "://" not in value:
        value = "http://" + value
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("The server address must start with http:// or https://.")
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"


def _ms_to_naive_utc(ms) -> datetime | None:
    try:
        return datetime.fromtimestamp(float(ms) / 1000.0, tz=timezone.utc).replace(tzinfo=None)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _call(client: httpx.Client, method: str, base: str, path: str, password: str, **kwargs):
    params = dict(kwargs.pop("params", {}) or {})
    params["guid"] = password  # BlueBubbles takes the server password as `guid`
    response = client.request(method, f"{base}/api/v1{path}", params=params, timeout=TIMEOUT, **kwargs)
    response.raise_for_status()
    body = response.json()
    if isinstance(body, dict) and body.get("status", 200) != 200:
        raise RuntimeError(body.get("message") or "The server refused the request.")
    return body.get("data") if isinstance(body, dict) else body


def _explain(error: Exception) -> str:
    if isinstance(error, ValueError):
        return str(error)
    if isinstance(error, httpx.HTTPStatusError):
        code = error.response.status_code
        if code in (401, 403):
            return "The server rejected the password. Check it in the BlueBubbles server settings."
        return f"The server answered with an error ({code})."
    if isinstance(error, httpx.ConnectError):
        return "Could not reach the server. Check the address, that the Mac is awake, and that you are on the same network or tunnel."
    if isinstance(error, httpx.TimeoutException):
        return "The server took too long to answer."
    return f"Unexpected error talking to BlueBubbles: {error}"


def check_connection(base_url: str, password: str, client: httpx.Client | None = None) -> dict:
    try:
        base = normalize_base_url(base_url)
        owned = client is None
        client = client or httpx.Client()
        try:
            _call(client, "GET", base, "/ping", password)
        finally:
            if owned:
                client.close()
        return {"accessible": True, "path": base, "error": None}
    except Exception as e:  # report, never raise: this feeds a status light
        return {"accessible": False, "path": (base_url or "").strip(), "error": _explain(e)}


def read_threads(base_url: str, password: str, max_threads: int = 50, max_messages: int = 50,
                 client: httpx.Client | None = None) -> dict:
    try:
        base = normalize_base_url(base_url)
        owned = client is None
        client = client or httpx.Client()
        try:
            chats = _call(client, "POST", base, "/chat/query", password, json={
                "limit": max_threads, "offset": 0, "with": ["participants", "lastMessage"], "sort": "lastmessage"})
            threads = []
            for chat in chats or []:
                guid = chat.get("guid")
                if not guid:
                    continue
                rows = _call(client, "GET", base, f"/chat/{guid}/message", password,
                             params={"limit": max_messages, "offset": 0, "sort": "DESC"}) or []
                messages = []
                for row in reversed(rows):
                    text = (row.get("text") or "").strip()
                    if not text:
                        continue
                    messages.append({
                        "message_id": str(row.get("guid") or ""),
                        "is_from_me": bool(row.get("isFromMe")),
                        "text": text,
                        "created_at": _ms_to_naive_utc(row.get("dateCreated")),
                        "service": "iMessage",
                    })
                if not messages:
                    continue
                handles = [p.get("address") for p in chat.get("participants") or [] if p.get("address")]
                identifier = chat.get("chatIdentifier") or guid
                threads.append({
                    "thread_id": guid,
                    "contact_name": chat.get("displayName") or (handles[0] if handles else identifier),
                    "handles": handles or [identifier],
                    "latest_message": messages[-1]["text"],
                    "latest_at": messages[-1]["created_at"],
                    "needs_response_estimate": _estimate_needs_response(messages),
                    "messages": messages,
                    "source_type": "imessage",
                })
        finally:
            if owned:
                client.close()
        return {"ok": True, "error": None, "threads": threads}
    except Exception as e:
        return {"ok": False, "error": _explain(e), "threads": []}
