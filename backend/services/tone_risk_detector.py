import re

DEFENSIVE_PATTERNS = [
    r"\bi (was|am) just\b", r"\bi didn'?t mean\b", r"\bfor the record\b",
    r"\bi never said\b", r"\bthat'?s not what i\b", r"\bi only\b.*\bbecause\b",
    r"\bto be clear\b.*\bi\b",
]
APOLOGETIC_PATTERNS = [
    r"\bso sorry\b", r"\breally sorry\b", r"\bi apologize\b", r"\bmy (bad|fault|mistake)\b",
    r"\bforgive me\b", r"\bsorry sorry\b", r"\bi'?m so so\b",
]
OVER_EXPLAINING_PATTERNS = [
    r"\band also\b.*\band also\b", r"\bbecause.*because\b", r"\bjust to clarify\b",
    r"\blet me explain\b", r"\bwhat i meant was\b", r"\bto be more specific\b",
]
VAGUE_PATTERNS = [
    r"\bsometime soon\b", r"\bmaybe later\b", r"\bwe'?ll see\b", r"\bpossibly\b.*\bmaybe\b",
    r"\bi'?ll (try to |)get back\b", r"\bif i (can|get a chance)\b",
]
COLD_PATTERNS = [
    r"^(ok|okay|fine|sure|noted|k)\.*$",
    r"^(acknowledged|received|understood)\.*$",
]
ANGRY_PATTERNS = [
    r"\b(ridiculous|absurd|unacceptable|pathetic|disgusting)\b",
    r"\byou (always|never)\b", r"\bthis is (insane|crazy|stupid)\b",
    r"\bi can'?t believe you\b",
]
NEEDY_PATTERNS = [
    r"\bplease please\b", r"\bjust (need|want) to know\b.*\bplease\b",
    r"\b(still|haven'?t) heard (from|back)\b",
    r"\bare you (mad|upset|angry) (at|with) me\b",
]
OVERSHARING_PATTERNS = [
    r"\bactually what (happened|is) is\b", r"\bso basically the whole story\b",
    r"\blong story but\b",
]
UNCLEAR_ASK_PATTERNS = [
    r"^(?!.*\?).*\b(wondering|curious|thinking)\b.*$",
]
INVENTED_FACTS_RISK_PATTERNS = [
    r"\bas (i|we) (said|mentioned|promised|agreed)\b",
    r"\blike (i|we) discussed\b", r"\bremember when\b",
]


def _check(text: str, patterns: list[str]) -> bool:
    lower = text.lower().strip()
    for p in patterns:
        if re.search(p, lower):
            return True
    return False


def detect_tone_risks(draft_text: str) -> dict:
    flags = []
    suggestions = []

    if _check(draft_text, DEFENSIVE_PATTERNS):
        flags.append("too_defensive")
        suggestions.append("Consider removing defensive framing — it often makes things worse.")

    if sum(1 for p in APOLOGETIC_PATTERNS if re.search(p, draft_text.lower())) >= 2:
        flags.append("too_apologetic")
        suggestions.append("Multiple apologies detected — one clear acknowledgment is usually stronger.")

    if _check(draft_text, OVER_EXPLAINING_PATTERNS):
        flags.append("over_explaining")
        suggestions.append("This might be over-explained. Try the 'more direct' or 'shorter' rewrite.")

    if _check(draft_text, VAGUE_PATTERNS):
        flags.append("vague")
        suggestions.append("Vague commitment detected — consider being specific or honest about uncertainty.")

    sentences = [s.strip() for s in draft_text.split(".") if s.strip()]
    if any(_check(s, COLD_PATTERNS) for s in sentences) and len(draft_text) < 30:
        flags.append("cold")
        suggestions.append("This reads as very cold or dismissive — even one warm word helps.")

    if _check(draft_text, ANGRY_PATTERNS):
        flags.append("angry")
        suggestions.append("Angry language detected. Try the 'calmer' rewrite before sending.")

    if _check(draft_text, NEEDY_PATTERNS):
        flags.append("needy")
        suggestions.append("This may come across as needy. Consider a more grounded tone.")

    if _check(draft_text, OVERSHARING_PATTERNS):
        flags.append("oversharing")
        suggestions.append("This might overshare context — keep it focused on what matters now.")

    if _check(draft_text, UNCLEAR_ASK_PATTERNS) and "?" not in draft_text:
        flags.append("unclear_ask")
        suggestions.append("The ask is unclear. Try ending with one specific question.")

    if _check(draft_text, INVENTED_FACTS_RISK_PATTERNS):
        flags.append("invented_facts_risk")
        suggestions.append("References a shared history — make sure this is accurate.")

    word_count = len(draft_text.split())
    if word_count > 120:
        flags.append("over_explaining")
        if "over_explaining" not in suggestions:
            suggestions.append("Draft is quite long — consider the 'shorter' rewrite.")

    severity = "none"
    if len(flags) >= 3:
        severity = "high"
    elif len(flags) >= 1:
        severity = "medium"

    return {
        "flags": flags,
        "severity": severity,
        "suggestions": suggestions,
        "word_count": word_count,
    }
