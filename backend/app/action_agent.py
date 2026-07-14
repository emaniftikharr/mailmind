"""
Action extractor: combines rule-based deadline detection with parallel LLM
extraction of meeting info and task list.

Public API
----------
extract_actions(subject, body, sender="", reference_date=None) -> dict
"""
import asyncio
from datetime import date
from typing import Optional

from app.chains.action_chain import MAX_INPUT_CHARS, get_action_chain
from app.chains.task_chain import _PRIORITIES, get_task_chain
from app.deadline_extractor import DeadlineHit, extract_deadlines

__all__ = ["extract_actions"]

# ── Coercion helpers ──────────────────────────────────────────────────────────

def _str(val, default: str = "") -> str:
    return str(val).strip() if val is not None else default

def _int_or_none(val) -> Optional[int]:
    try:
        return int(val)
    except (TypeError, ValueError):
        return None

def _str_list(val) -> list[str]:
    if not isinstance(val, list):
        return []
    return [str(x).strip() for x in val if x]

def _bool(val, default: bool = False) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "yes", "1")
    return default

# ── Meeting ───────────────────────────────────────────────────────────────────

_MEETING_FALLBACK: dict = {
    "meeting_detected": False, "title": "", "date_str": "", "time_str": "",
    "duration_minutes": None, "location": "", "organizer": "", "attendees": [],
    "agenda": "", "is_tentative": False, "extraction_error": None,
}

def _coerce_meeting(raw: dict) -> dict:
    return {
        "meeting_detected":  _bool(raw.get("meeting_detected"), False),
        "title":             _str(raw.get("title")),
        "date_str":          _str(raw.get("date_str")),
        "time_str":          _str(raw.get("time_str")),
        "duration_minutes":  _int_or_none(raw.get("duration_minutes")),
        "location":          _str(raw.get("location")),
        "organizer":         _str(raw.get("organizer")),
        "attendees":         _str_list(raw.get("attendees", [])),
        "agenda":            _str(raw.get("agenda")),
        "is_tentative":      _bool(raw.get("is_tentative"), False),
        "extraction_error":  None,
    }

async def _safe_meeting(email_text: str) -> dict:
    try:
        raw: dict = await get_action_chain().ainvoke({"email_text": email_text})
        return _coerce_meeting(raw)
    except Exception as exc:
        return {**_MEETING_FALLBACK, "extraction_error": str(exc)}

# ── Tasks ─────────────────────────────────────────────────────────────────────

_ASSIGNEES = frozenset({"me", "them", "other"})

def _coerce_task(raw: dict) -> dict | None:
    title = _str(raw.get("title"))
    if not title:
        return None
    assignee = _str(raw.get("assignee", "me"))
    if assignee not in _ASSIGNEES:
        assignee = "other"
    priority = _str(raw.get("priority", "normal"))
    if priority not in _PRIORITIES:
        priority = "normal"
    return {
        "title":        title,
        "description":  _str(raw.get("description")),
        "assignee":     assignee,
        "due_date_str": _str(raw.get("due_date_str")),
        "priority":     priority,
    }

def _coerce_tasks(raw: dict) -> list[dict]:
    raw_list = raw.get("tasks", [])
    if not isinstance(raw_list, list):
        return []
    return [t for raw_t in raw_list if (t := _coerce_task(raw_t)) is not None]

async def _safe_tasks(email_text: str) -> list[dict]:
    try:
        raw: dict = await get_task_chain().ainvoke({"email_text": email_text})
        return _coerce_tasks(raw)
    except Exception:
        return []

# ── Public orchestrator ───────────────────────────────────────────────────────

async def extract_actions(
    subject: str,
    body: str,
    sender: str = "",
    reference_date: Optional[date] = None,
) -> dict:
    """
    Extract meetings, deadlines, and tasks from an email.

    Meeting extraction and task extraction run in parallel via asyncio.gather.
    Deadline extraction is synchronous (rule-based, always succeeds).

    Returns
    -------
    {
      "meeting":      MeetingModel dict,
      "deadlines":    list[DeadlineModel dict],
      "tasks":        list[TaskModel dict],
      "has_meeting":  bool,
      "has_deadlines": bool,
      "has_tasks":    bool,
    }
    """
    combined = f"Subject: {subject}\n\nBody:\n{body}" if subject else body
    email_text = combined[:MAX_INPUT_CHARS]

    # Deadline extraction is synchronous — run first, no blocking
    deadlines: list[DeadlineHit] = extract_deadlines(
        combined, reference_date=reference_date
    )

    # Meeting + task extraction run in parallel
    meeting, tasks = await asyncio.gather(
        _safe_meeting(email_text),
        _safe_tasks(email_text),
    )

    return {
        "meeting":       meeting,
        "deadlines":     [d.to_dict() for d in deadlines],
        "tasks":         tasks,
        "has_meeting":   meeting["meeting_detected"],
        "has_deadlines": len(deadlines) > 0,
        "has_tasks":     len(tasks) > 0,
    }
