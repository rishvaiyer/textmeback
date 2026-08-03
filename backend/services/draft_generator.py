import json
import re
from backend.config import load_settings
from backend.services.prompt_builder import build_draft_prompt, build_rewrite_prompt
from backend.services.style_profile import get_profile
from backend.services.tone_risk_detector import detect_tone_risks
from backend.services.token_estimator import estimate_and_record


def _mock_draft(thread: dict) -> dict:
    messages = thread.get("messages", [])
    contact = thread.get("contact_name", "Unknown")
    category = thread.get("category", "unknown")
    priority = thread.get("priority_label", "low_priority")

    recent_inbound = [m for m in messages if not m.get("is_from_me")][-3:]
    last_msg = recent_inbound[-1].get("text", "") if recent_inbound else ""

    has_question = "?" in last_msg
    is_scheduling = any(w in last_msg.lower() for w in ["meet", "call", "free", "available", "when", "time"])
    is_emotional = any(w in last_msg.lower() for w in ["sorry", "miss", "love", "upset", "hurt", "sad"])
    is_urgent = priority in ("urgent",) or any(w in last_msg.lower() for w in ["urgent", "asap", "today", "deadline"])

    if not thread.get("needs_response_estimate"):
        draft = "No reply seems needed here."
        cat = "no_reply_needed"
        urgency = "low"
        confidence = "medium"
        reason = "Last message was from you or thread looks caught up."
    elif is_urgent:
        draft = f"On it — I'll get back to you very soon."
        cat = "reply_needed"
        urgency = "high"
        confidence = "low"
        reason = "Urgent signal detected. Draft is a placeholder — edit before sending."
    elif is_scheduling:
        draft = "When works for you? I'm flexible this week."
        cat = "scheduling"
        urgency = "medium"
        confidence = "medium"
        reason = "Scheduling thread — generic placeholder, add your actual availability."
    elif is_emotional:
        draft = "Hey — I hear you. Let's talk soon."
        cat = "emotional"
        urgency = "medium"
        confidence = "low"
        reason = "Emotional context detected. Placeholder only — this needs your personal touch."
    elif has_question:
        draft = f"Good question — let me think on that and get back to you."
        cat = "question"
        urgency = "medium"
        confidence = "low"
        reason = "Question detected. Placeholder — fill in your actual answer."
    else:
        draft = "Got it, thanks for the update!"
        cat = "reply_needed"
        urgency = "low"
        confidence = "low"
        reason = "No LLM configured. This is a generic placeholder — edit before sending."

    return {
        "urgency": urgency,
        "category": cat,
        "draft_reply": draft,
        "reason": reason,
        "risk_flags": [],
        "confidence": confidence,
        "mode": "mock",
    }


def _llm_draft(thread: dict, api_key: str, model: str) -> dict:
    try:
        import anthropic
    except ImportError:
        return {**_mock_draft(thread), "error": "anthropic package not installed"}

    profile = get_profile()
    prompt = build_draft_prompt(thread, profile)

    estimate_and_record("draft_generation", model, prompt, expected_output_tokens=200)

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()

    json_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if not json_match:
        return {**_mock_draft(thread), "error": "LLM returned non-JSON"}

    data = json.loads(json_match.group(0))
    data["mode"] = "llm"
    return data


def generate_draft(thread: dict) -> dict:
    settings = load_settings()
    api_key = settings.get("llm_api_key", "")
    model = settings.get("llm_model", "claude-haiku-4-5-20251001")
    local_only = settings.get("local_only_mode", True)

    if api_key and not local_only:
        try:
            result = _llm_draft(thread, api_key, model)
        except Exception as e:
            result = {**_mock_draft(thread), "error": str(e)}
    else:
        result = _mock_draft(thread)

    draft_text = result.get("draft_reply", "")
    tone_analysis = detect_tone_risks(draft_text)
    result["tone_risks"] = tone_analysis

    return result


def rewrite_draft(draft_text: str, rewrite_type: str, contact_tone: str = "unknown") -> str:
    settings = load_settings()
    api_key = settings.get("llm_api_key", "")
    model = settings.get("llm_model", "claude-haiku-4-5-20251001")
    local_only = settings.get("local_only_mode", True)

    profile = get_profile()

    if api_key and not local_only:
        try:
            import anthropic
            prompt = build_rewrite_prompt(draft_text, rewrite_type, profile, contact_tone)
            estimate_and_record("rewrite", model, prompt, expected_output_tokens=150)
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=model,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except Exception:
            pass

    return _mock_rewrite(draft_text, rewrite_type)


def _mock_rewrite(text: str, rewrite_type: str) -> str:
    words = text.split()
    if rewrite_type == "shorter":
        return " ".join(words[: max(5, len(words) // 2)])
    elif rewrite_type == "casual":
        return text.lower().rstrip(".").rstrip("!") + " :)"
    elif rewrite_type == "professional":
        return text.capitalize().rstrip(" ").rstrip("!") + "."
    elif rewrite_type == "less_apologetic":
        cleaned = re.sub(r"(sorry|i apologize|my bad|my fault)[,.]?\s*", "", text, flags=re.IGNORECASE).strip()
        return cleaned if cleaned else text
    elif rewrite_type == "calmer":
        calm = re.sub(r"\b(ridiculous|insane|unacceptable|crazy|absurd)\b", "concerning", text, flags=re.IGNORECASE)
        return calm
    elif rewrite_type == "say_no_politely":
        return f"Thanks for thinking of me — I won't be able to make this work, but I appreciate you reaching out."
    elif rewrite_type == "buy_time":
        return f"Thanks for this — I need a bit more time to think it through. I'll get back to you shortly."
    elif rewrite_type == "ask_one_clear_question":
        base = text.rstrip("?.!") + "."
        return base + " What would be most helpful for me to know first?"
    else:
        return text + f" [{rewrite_type}]"
