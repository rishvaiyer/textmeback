from backend.services.style_profile import build_style_instructions


REWRITE_INSTRUCTIONS = {
    "shorter": "Rewrite this reply to be significantly shorter. Cut anything unnecessary. Keep the core message.",
    "nicer": "Rewrite this reply to be warmer and more considerate without being fake.",
    "more_direct": "Rewrite this reply to be more direct. Lead with the main point.",
    "less_fake": "Rewrite this reply to sound like a real human, not a polished assistant. Remove corporate language.",
    "more_adult": "Rewrite this reply to sound more composed, clear, and mature.",
    "casual": "Rewrite this reply in a casual, friendly tone. Lowercase is fine.",
    "professional": "Rewrite this reply in a calm, professional tone. Brief and consultant-like.",
    "say_no_politely": "Rewrite this reply to say no clearly but politely, without over-explaining.",
    "buy_time": "Rewrite this reply to acknowledge the message and buy more time to respond properly.",
    "ask_one_clear_question": "Rewrite this reply to end with exactly one clear, specific question.",
    "calmer": "Rewrite this reply to be calmer and less reactive. Remove any heated language.",
    "less_defensive": "Rewrite this reply removing defensive framing. Just state your view plainly.",
    "less_apologetic": "Rewrite this reply reducing apologies. One acknowledgment max.",
}


def build_draft_prompt(thread: dict, style_profile: dict) -> str:
    messages = thread.get("messages", [])
    contact = thread.get("contact_name", "Unknown")
    tone = thread.get("contact_tone", "unknown")

    style_instructions = build_style_instructions(style_profile, tone)

    conversation_lines = []
    for msg in messages[-15:]:
        speaker = "Me" if msg.get("is_from_me") else contact
        text = (msg.get("text") or "").strip()
        if text:
            conversation_lines.append(f"{speaker}: {text}")

    conversation = "\n".join(conversation_lines)

    return f"""You are drafting a reply for the user in their personal messaging app.

{style_instructions}

Conversation with {contact}:
{conversation}

Draft a reply the user might send. Output ONLY valid JSON with this exact structure:
{{
  "urgency": "low | medium | high",
  "category": "reply_needed | no_reply_needed | emotional | scheduling | question | work | unknown",
  "draft_reply": "the reply text",
  "reason": "one short sentence explaining why this draft",
  "risk_flags": ["sensitive", "medical", "money", "legal", "conflict", "work_risk", "unknown_context"],
  "confidence": "low | medium | high"
}}

Rules:
- draft_reply must be what the user would actually send
- Do not invent facts or history
- Do not over-apologize
- If context is unclear, ask one clear question
- risk_flags should only include flags that apply; empty array is fine
- Output ONLY the JSON object, no other text"""


def build_rewrite_prompt(draft_text: str, rewrite_type: str, style_profile: dict, contact_tone: str = "unknown") -> str:
    instruction = REWRITE_INSTRUCTIONS.get(rewrite_type, f"Rewrite this reply: {rewrite_type}")
    style_instructions = build_style_instructions(style_profile, contact_tone)

    return f"""You are rewriting a message draft.

{style_instructions}

Original draft:
{draft_text}

Task: {instruction}

Output ONLY the rewritten reply text. No explanation, no JSON, no quotes around it."""
