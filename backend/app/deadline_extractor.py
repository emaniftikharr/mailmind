"""
Rule-based deadline extractor — no LLM, no network.

Detects phrases like "by Friday", "due next week", "deadline July 18",
"ASAP", "within 3 days" and resolves them to ISO dates where possible.

Pass reference_date in tests for deterministic output; defaults to today.
"""
import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

# ── Date helpers ───────────────────────────────────────────────────────────────

_MONTH_NUM: dict[str, int] = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

_WEEKDAY_NUM: dict[str, int] = {
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6,
}


def _month(name: str) -> int:
    return _MONTH_NUM.get(name.lower()[:3], 0)


def _weekday(name: str) -> int:
    return _WEEKDAY_NUM.get(name.lower()[:3], -1)


def _this_weekday(ref: date, wd: int) -> date:
    """Nearest occurrence of weekday wd, including today."""
    days = (wd - ref.weekday()) % 7
    return ref + timedelta(days=days)


def _next_weekday(ref: date, wd: int) -> date:
    """Next occurrence of weekday wd, skipping today (≥ 1 day)."""
    days = (wd - ref.weekday()) % 7
    return ref + timedelta(days=days if days > 0 else 7)


def _end_of_week(ref: date) -> date:
    """Next Friday (business end-of-week), or today if today is Friday."""
    return _this_weekday(ref, 4)


def _start_of_next_week(ref: date) -> date:
    """Monday that opens the next calendar week (always ≥ 1 day away)."""
    days = (7 - ref.weekday()) % 7
    return ref + timedelta(days=days if days > 0 else 7)


def _end_of_month(ref: date) -> date:
    # Last day of ref's month
    if ref.month == 12:
        return date(ref.year, 12, 31)
    return date(ref.year, ref.month + 1, 1) - timedelta(days=1)


def _urgency_from_delta(delta_days: int) -> str:
    if delta_days < 0:
        return "overdue"
    if delta_days == 0:
        return "today"
    if delta_days == 1:
        return "tomorrow"
    if delta_days <= 7:
        return "this_week"
    if delta_days <= 14:
        return "next_week"
    if delta_days <= 31:
        return "this_month"
    return "future"


# ── Pattern registry ──────────────────────────────────────────────────────────

# Deadline-indicator prefix — must precede date expressions in Category A
_DI = (
    r"(?:by|due(?:\s+by)?|before|no\s+later\s+than"
    r"|deadline\s*[:\-]?\s*"
    r"|must\s+(?:be\s+)?(?:in|done|complet\w+|submit\w+|deliver\w+|sent?)\s+by"
    r"|(?:submit|deliver|complet\w+|send|return|respond)\s+by)"
)

_WDAYS = (
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday"
    r"|mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)"
)

_MONTHS = (
    r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?"
    r"|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?"
    r"|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)

# Each entry: (kind, compiled_pattern)
# Kinds are resolved in _resolve() below
_PATTERNS: list[tuple[str, re.Pattern]] = []


def _add(kind: str, pat: str) -> None:
    _PATTERNS.append((kind, re.compile(pat, re.IGNORECASE)))


# ── Category A: require deadline indicator ────────────────────────────────────
# This-weekday ("by Friday", "due Wednesday")
_add("this_weekday",   rf"{_DI}\s+(?:this\s+)?{_WDAYS}")
# Next-weekday ("by next Monday", "due next Thursday")
_add("next_weekday",   rf"{_DI}\s+next\s+{_WDAYS}")
# Tomorrow ("by tomorrow", "due tomorrow")
_add("tomorrow",       rf"{_DI}\s+tomorrow")
# End of today ("by end of day", "by EOD")
_add("today",          rf"{_DI}\s+(?:end\s+of\s+(?:the\s+)?(?:business\s+)?day|today|eod)")
# End of week ("by end of week", "due EOW")
_add("end_of_week",    rf"{_DI}\s+(?:(?:the\s+)?end\s+of\s+(?:this\s+)?week|eow)")
# Next week ("by next week", "due next week")
_add("next_week",      rf"{_DI}\s+next\s+week")
# End of month ("by end of month", "due EOM")
_add("end_of_month",   rf"{_DI}\s+(?:(?:the\s+)?end\s+of\s+(?:this\s+)?month|eom)")
# Next month ("by next month")
_add("next_month",     rf"{_DI}\s+next\s+month")
# Within N days / weeks
_add("within_days",    r"within\s+(\d+)\s+(?:business\s+)?days?")
_add("within_weeks",   r"within\s+(\d+)\s+weeks?")
# Absolute: "by July 18" / "by July 18th [, 2026]"
_add("abs_month_day",
     rf"{_DI}\s+{_MONTHS}\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{{4}}))?")
# Absolute: "by 18 July" / "by the 18th of July"
_add("abs_day_month",
     rf"{_DI}\s+(?:the\s+)?(\d{{1,2}})(?:st|nd|rd|th)?(?:\s+of)?\s+{_MONTHS}(?:\s*,?\s*(\d{{4}}))?")
# Absolute numeric: "by 07/18" or "by 07/18/26"
_add("abs_numeric",
     rf"{_DI}\s+(\d{{1,2}})/(\d{{1,2}})(?:/(\d{{2,4}}))?")

# ── Category B: self-contained phrases (no indicator required) ────────────────
_add("asap",
     r"\b(?:asap|as\s+soon\s+as\s+possible|right\s+away|straight\s+away)\b")
_add("today_b",
     r"\b(?:eod|end\s+of\s+(?:the\s+)?(?:business\s+)?day|close\s+of\s+business|cob)\b")
_add("end_of_week_b",
     r"\b(?:eow|end\s+of\s+(?:the\s+)?week)\b")
_add("end_of_month_b",
     r"\b(?:eom|end\s+of\s+(?:the\s+)?month)\b")


# ── Resolver ──────────────────────────────────────────────────────────────────

def _resolve(kind: str, m: re.Match, ref: date) -> tuple[Optional[date], str, bool]:
    """
    Return (resolved_date, confidence, is_relative).
    resolved_date is None for ASAP / unknown.
    """
    g = m.groups()  # convenience

    if kind in ("this_weekday",):
        wd = _weekday(g[-1])  # last capture = weekday name
        if wd < 0:
            return None, "low", True
        return _this_weekday(ref, wd), "high", True

    if kind == "next_weekday":
        wd = _weekday(g[-1])
        if wd < 0:
            return None, "low", True
        # "next X" = skip current week occurrence
        base = _this_weekday(ref, wd)
        resolved = base if base > ref else base + timedelta(days=7)
        # Always at least 1 week away from today's occurrence
        if (resolved - ref).days <= 0:
            resolved += timedelta(days=7)
        return resolved, "high", True

    if kind in ("today", "today_b"):
        return ref, "high", True

    if kind == "tomorrow":
        return ref + timedelta(days=1), "high", True

    if kind in ("end_of_week", "end_of_week_b"):
        return _end_of_week(ref), "high", True

    if kind == "next_week":
        return _start_of_next_week(ref), "medium", True

    if kind in ("end_of_month", "end_of_month_b"):
        return _end_of_month(ref), "high", True

    if kind == "next_month":
        # First day of next month
        if ref.month == 12:
            return date(ref.year + 1, 1, 31), "medium", True
        nm = ref.month + 1
        # last day of next month
        if nm == 12:
            last = 31
        else:
            last = (date(ref.year, nm + 1, 1) - timedelta(days=1)).day
        return date(ref.year, nm, last), "medium", True

    if kind == "within_days":
        n = int(g[0])
        return ref + timedelta(days=n), "high", True

    if kind == "within_weeks":
        n = int(g[0])
        return ref + timedelta(weeks=n), "high", True

    if kind == "abs_month_day":
        # groups: (month_name, day, year_or_None)
        month_name, day_str, year_str = g[0], g[1], g[2] if len(g) > 2 else None
        mn = _month(month_name)
        if not mn:
            return None, "low", False
        day = int(day_str)
        year = int(year_str) if year_str else ref.year
        if year < 100:
            year += 2000
        try:
            d = date(year, mn, day)
            # If the date has already passed this year and no year was specified, use next year
            if d < ref and not year_str:
                d = date(year + 1, mn, day)
            return d, "high", False
        except ValueError:
            return None, "low", False

    if kind == "abs_day_month":
        # groups: (day, month_name, year_or_None)
        day_str, month_name, year_str = g[0], g[1], g[2] if len(g) > 2 else None
        mn = _month(month_name)
        if not mn:
            return None, "low", False
        day = int(day_str)
        year = int(year_str) if year_str else ref.year
        if year < 100:
            year += 2000
        try:
            d = date(year, mn, day)
            if d < ref and not year_str:
                d = date(year + 1, mn, day)
            return d, "high", False
        except ValueError:
            return None, "low", False

    if kind == "abs_numeric":
        # groups: (month_num, day_num, year_or_None) — US format MM/DD
        mn, day, year_str = int(g[0]), int(g[1]), g[2] if len(g) > 2 else None
        year = int(year_str) if year_str else ref.year
        if year < 100:
            year += 2000
        try:
            d = date(year, mn, day)
            if d < ref and not year_str:
                d = date(year + 1, mn, day)
            return d, "medium", False
        except ValueError:
            return None, "low", False

    if kind == "asap":
        return None, "high", True  # no specific date — return None

    return None, "low", True


# ── Public types ──────────────────────────────────────────────────────────────

@dataclass
class DeadlineHit:
    phrase: str             # exact substring that triggered the match
    resolved_date: Optional[str]  # ISO 8601 date, or None for "ASAP"
    confidence: str         # "high" | "medium" | "low"
    is_relative: bool       # True when phrase used relative language
    urgency: str            # "today" | "tomorrow" | "this_week" | "next_week" | "this_month" | "future" | "asap" | "overdue"

    def to_dict(self) -> dict:
        return {
            "phrase":        self.phrase,
            "resolved_date": self.resolved_date,
            "confidence":    self.confidence,
            "is_relative":   self.is_relative,
            "urgency":       self.urgency,
        }


# ── Main extractor ────────────────────────────────────────────────────────────

def extract_deadlines(
    text: str,
    reference_date: Optional[date] = None,
) -> list[DeadlineHit]:
    """
    Scan text for deadline phrases and resolve them to dates.

    Args:
        text:           Subject + body of the email (plain text).
        reference_date: Date to resolve relative expressions against.
                        Defaults to date.today().
    Returns:
        Ordered list of DeadlineHit objects, deduplicated by span.
    """
    ref = reference_date or date.today()
    hits: list[DeadlineHit] = []
    covered_spans: set[tuple[int, int]] = set()

    for kind, pat in _PATTERNS:
        for m in pat.finditer(text):
            span = (m.start(), m.end())
            # Skip if this span is already covered by an earlier (higher-priority) match
            if any(s <= span[0] and span[1] <= e for s, e in covered_spans):
                continue

            resolved_date_obj, confidence, is_relative = _resolve(kind, m, ref)

            if kind == "asap":
                urgency = "asap"
                iso = None
            elif resolved_date_obj is None:
                urgency = "unknown"
                iso = None
            else:
                delta = (resolved_date_obj - ref).days
                urgency = _urgency_from_delta(delta)
                iso = resolved_date_obj.isoformat()

            phrase = text[m.start():m.end()].strip()
            hits.append(DeadlineHit(
                phrase=phrase,
                resolved_date=iso,
                confidence=confidence,
                is_relative=is_relative,
                urgency=urgency,
            ))
            covered_spans.add(span)

    return hits
