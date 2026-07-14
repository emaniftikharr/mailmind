"""
Public API for phishing / social-engineering detection.

Delegates to the LangChain LCEL chain in app.chains.phishing_chain.
On persistent failure (all 3 retries exhausted) returns a safe-default
'suspicious' verdict rather than propagating an error to the router —
erring on the side of caution so the user is never silently exposed.
"""
from app.chains.phishing_chain import (
    INDICATOR_NAMES,
    MAX_INPUT_CHARS,
    VERDICTS,
    get_phishing_chain,
)

__all__ = ["detect_phishing", "INDICATOR_NAMES", "VERDICTS"]

_SAFE_FALLBACK = {
    "verdict": "suspicious",
    "risk_score": 0.5,
    "indicators": [],
    "explanation": "Phishing detection unavailable — treat with caution.",
    "safe_to_open": False,
}


def _coerce_verdict(raw: str) -> str:
    return raw if raw in VERDICTS else "suspicious"


def _coerce_indicators(raw: list) -> list[str]:
    return [i for i in raw if isinstance(i, str) and i in INDICATOR_NAMES]


def _coerce_safe(verdict: str, risk_score: float, raw_safe) -> bool:
    if verdict == "phishing":
        return False
    if verdict == "suspicious" and risk_score >= 0.5:
        return False
    if isinstance(raw_safe, bool):
        return raw_safe
    return True


async def detect_phishing(
    subject: str,
    body: str,
    sender: str = "",
) -> dict:
    lines = []
    if sender:
        lines.append(f"From: {sender}")
    lines.append(f"Subject: {subject}")
    lines.append(f"\nBody:\n{body}")
    email_text = "\n".join(lines)[:MAX_INPUT_CHARS]

    try:
        data: dict = await get_phishing_chain().ainvoke({"email_text": email_text})
    except Exception as exc:
        return {
            **_SAFE_FALLBACK,
            "explanation": f"Detection unavailable: {exc}",
        }

    verdict    = _coerce_verdict(data.get("verdict", "suspicious"))
    risk_score = round(float(data.get("risk_score", 0.5)), 2)
    indicators = _coerce_indicators(data.get("indicators", []))
    explanation = str(data.get("explanation", ""))
    safe_to_open = _coerce_safe(verdict, risk_score, data.get("safe_to_open"))

    return {
        "verdict":     verdict,
        "risk_score":  risk_score,
        "indicators":  indicators,
        "explanation": explanation,
        "safe_to_open": safe_to_open,
    }
