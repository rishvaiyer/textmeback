"""Where messages come from: this Mac's own Messages database, or a BlueBubbles server.

`message_source` in the settings picks one. The default is the local database, so existing installs
behave exactly as before.
"""
from backend.config import load_settings
from backend.services import bluebubbles_reader, imessage_reader

LOCAL = "imessage"
BLUEBUBBLES = "bluebubbles"


def current_source(settings: dict | None = None) -> str:
    settings = settings if settings is not None else load_settings()
    return BLUEBUBBLES if settings.get("message_source") == BLUEBUBBLES else LOCAL


def source_status() -> dict:
    """Same shape as the old iMessage access check, plus which source answered."""
    settings = load_settings()
    if current_source(settings) == BLUEBUBBLES:
        status = bluebubbles_reader.check_connection(
            settings.get("bluebubbles_url", ""), settings.get("bluebubbles_password", ""))
        return {**status, "source": BLUEBUBBLES}
    return {**imessage_reader.check_imessage_access(), "source": LOCAL}


def read_source_threads() -> dict:
    settings = load_settings()
    if current_source(settings) == BLUEBUBBLES:
        return bluebubbles_reader.read_threads(
            settings.get("bluebubbles_url", ""), settings.get("bluebubbles_password", ""),
            max_threads=settings.get("max_threads", 50),
            max_messages=settings.get("max_messages_per_thread", 50))
    return imessage_reader.read_threads()
