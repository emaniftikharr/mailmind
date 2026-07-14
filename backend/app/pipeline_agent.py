"""
Phase 2 pipeline orchestrator.

Execution order
---------------
Wave 1 — start all independent tasks simultaneously:
  • classify_email       (async LLM — 8b, fast)
  • detect_phishing      (async LLM — 8b, fast)
  • _run_risk            (sync rule-based — links + trust, sub-ms)

Await classify (others keep running in background).

Wave 2 — start classification-dependent tasks with category/priority:
  • extract_actions      (async LLM — 8b, already internal parallel)
  • generate_replies     (async LLM — 8b)

Final gather: phishing + risk + actions + replies.

Total wall-clock ≈ max(classify, phishing) + max(actions, replies),
rather than the sum of all six calls.
"""
import asyncio
import time

from app.action_agent import extract_actions
from app.classification_agent import classify_email
from app.link_analyzer import analyze_email_links
from app.phishing_agent import detect_phishing
from app.reply_agent import generate_replies
from app.social_engineering import analyze_trust

__all__ = ["run_pipeline"]


def _serialize_trust(report) -> dict:
    return {
        "trust_score":           report.trust_score,
        "risk_level":            report.risk_level,
        "urgency_hits":          [
            {"category": h.category, "matched_text": h.matched_text}
            for h in report.urgency_hits
        ],
        "urgency_categories":    report.urgency_categories,
        "credential_hits":       [
            {"category": h.category, "matched_text": h.matched_text}
            for h in report.credential_hits
        ],
        "credential_categories": report.credential_categories,
        "link_flags":            report.link_flags,
        "score_breakdown":       report.score_breakdown,
        "summary":               report.summary,
    }


async def _run_risk(subject: str, body: str, is_html: bool) -> tuple[dict, dict]:
    """
    Rule-based (non-LLM) link and trust analysis.  Both calls are pure Python
    regex — sub-millisecond — so running them directly in the event loop is
    cheaper than scheduling a thread.
    """
    link_data = analyze_email_links(body, subject=subject, is_html=is_html)
    trust_report = analyze_trust(subject, body, link_flags=link_data["risk_flags"])
    return link_data, _serialize_trust(trust_report)


async def run_pipeline(
    subject: str,
    body: str,
    sender: str = "",
    is_html: bool = False,
) -> dict:
    """
    Run all Phase 2 agents with maximum parallelism and return a single
    unified result dict containing all six section outputs plus elapsed_ms.

    Every individual agent already handles its own errors and returns safe
    fallback values, so this function does not add extra try/except wrappers.
    """
    t0 = time.monotonic()

    # ── Wave 1: independent tasks — all start immediately ─────────────────────
    classify_task = asyncio.create_task(classify_email(subject, body))
    phishing_task = asyncio.create_task(detect_phishing(subject, body, sender))
    risk_task     = asyncio.create_task(_run_risk(subject, body, is_html))

    # Block only on classification so Wave 2 can start as soon as category is known.
    # phishing_task and risk_task continue running in the background.
    classification = await classify_task
    category = classification.get("category", "")
    priority = classification.get("priority", "normal")

    # ── Wave 2: classification-dependent tasks ─────────────────────────────────
    actions_task = asyncio.create_task(extract_actions(subject, body, sender))
    replies_task = asyncio.create_task(
        generate_replies(subject, body, sender, category=category, priority=priority)
    )

    # Gather all remaining tasks — most will already be done or near-done
    phishing, (link_data, trust_dict), actions, replies = await asyncio.gather(
        phishing_task,
        risk_task,
        actions_task,
        replies_task,
    )

    return {
        "classification": classification,
        "phishing":       phishing,
        "trust":          trust_dict,
        "links":          link_data,
        "actions":        actions,
        "replies":        replies,
        "elapsed_ms":     round((time.monotonic() - t0) * 1000),
    }
