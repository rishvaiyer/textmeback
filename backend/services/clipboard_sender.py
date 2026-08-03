def copy_to_clipboard(text: str) -> dict:
    """
    On macOS, pyperclip uses pbcopy. On Linux fallback: xclip/xsel.
    In headless/server environments this may fail gracefully.
    """
    try:
        import pyperclip
        pyperclip.copy(text)
        return {"ok": True, "method": "pyperclip"}
    except Exception as e:
        return {"ok": False, "error": str(e), "fallback": "use browser clipboard API"}
