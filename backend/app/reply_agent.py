"""
Smart reply generator: uses email content + optional classification metadata
to generate 2-3 reply variants with distinct intents.

Public API
----------
generate_replies(subject, body, sender="", category="", priority="normal") -> dict
"""
from app.chains.reply_chain import MAX_INPUT_CHARS, get_reply_chain

__all__ = ["generate_replies"]

_VALID_TONES = frozenset({"formal", "friendly", "direct"})
_VALID_TONES_DEFAULT = "professional"


def _str(val, default: str = "") -> str:
    return str(val).strip() if val is not None else default


def _coerce_variant(raw: dict) -> dict | None:
    label = _str(raw.get("label"))
    text  = _str(raw.get("text"))
    if not label or not text:
        return None
    tone = _str(raw.get("tone", _VALID_TONES_DEFAULT))
    if tone not in _VALID_TONES:
        tone = _VALID_TONES_DEFAULT
    return {"label": label, "tone": tone, "text": text}


def _coerce_variants(raw: dict) -> list[dict]:
    raw_list = raw.get("variants", [])
    if not isinstance(raw_list, list):
        return []
    return [v for item in raw_list if (v := _coerce_variant(item)) is not None]


async def generate_replies(
    subject: str,
    body: str,
    sender: str = "",
    category: str = "",
    priority: str = "normal",
) -> dict:
    """
    Generate 2-3 smart reply variants for an email.

    Returns
    -------
    {
      "variants": [{ "label", "tone", "text" }],
      "count":    int,
    }
    """
    # Prepend classification hints if available — the LLM uses them to pick
    # contextually appropriate variant intents (Accept/Decline vs Acknowledge/etc.)
    meta = f"[Category: {category} | Priority: {priority}]" if category else ""
    from_line = f"From: {sender}" if sender else ""
    parts = [p for p in [meta, f"Subject: {subject}", from_line, "", body] if p is not None]
    email_text = "\n".join(parts).strip()[:MAX_INPUT_CHARS]

    try:
        raw: dict = await get_reply_chain().ainvoke({"email_text": email_text})
        reply_needed = bool(raw.get("reply_needed", True))
        variants = [] if not reply_needed else _coerce_variants(raw)
    except Exception:
        reply_needed = True
        variants = []

    return {"variants": variants, "count": len(variants), "reply_needed": reply_needed}
