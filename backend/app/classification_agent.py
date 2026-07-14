"""
Public API for email classification.

Delegates to the LangChain LCEL chain in app.chains.classification_chain.
The chain retries up to 3 times on any exception before raising; this module
catches that final failure and returns a safe-default response instead of
propagating an error to the router.
"""
from app.chains.classification_chain import (
    CATEGORY_NAMES,
    MAX_INPUT_CHARS,
    PRIORITY_NAMES,
    get_classification_chain,
)

# Re-export so existing imports from this module keep working
__all__ = ["CATEGORY_NAMES", "PRIORITY_NAMES", "classify_email"]

_FALLBACK = {
    "category": "update",
    "priority": "normal",
    "confidence": 0.0,
    "reason": "Classification unavailable — all retry attempts failed.",
}


async def classify_email(subject: str, body: str) -> dict:
    combined = f"Subject: {subject}\n\nBody:\n{body}"
    email_text = combined[:MAX_INPUT_CHARS]

    try:
        data: dict = await get_classification_chain().ainvoke({"email_text": email_text})
    except Exception as exc:
        return {
            **_FALLBACK,
            "reason": f"Classification unavailable: {exc}",
            "all_categories": CATEGORY_NAMES,
            "all_priorities": PRIORITY_NAMES,
        }

    category = data.get("category", "update")
    if category not in CATEGORY_NAMES:
        category = "update"

    priority = data.get("priority", "normal")
    if priority not in PRIORITY_NAMES:
        priority = "normal"

    return {
        "category": category,
        "priority": priority,
        "confidence": round(float(data.get("confidence", 0.0)), 2),
        "reason": data.get("reason", ""),
        "all_categories": CATEGORY_NAMES,
        "all_priorities": PRIORITY_NAMES,
    }
