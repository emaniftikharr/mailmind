"""
Reply text quality inspection — backend/tests/test_reply_quality.py

Checks every returned variant for formatting/quality issues rather than
boolean pass/fail.  Prints the full reply text so issues can be spotted
visually.

Checks per variant
------------------
  [words]    word count in range [10, 150]
  [name]     contains "[Your Name]" exactly (sign-off requirement)
  [no-md]    no Markdown artifacts (##, **, __, ```, ---)
  [no-ai]    does not start with AI filler ("Certainly", "Sure,", "Of course")
  [no-subj]  does not contain "Subject:" — body only, no header
  [label]    label is 1-5 words, no punctuation except spaces and hyphens

Overall pass if <= 1 failure across all checked variants.

Run: python backend/tests/test_reply_quality.py
"""
import asyncio
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, "backend")

_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

from app.reply_agent import generate_replies

# ── Quality checkers ────────────────────────────────────────────────────────

_MARKDOWN_RE = re.compile(r"(##|(?<!\[)\*\*|\b__\b|```|(?<!\w)---(?!\w))")
_AI_FILLER_RE = re.compile(r"^(certainly|sure,|of course|absolutely,|great,)", re.IGNORECASE)
_LABEL_RE = re.compile(r"^[\w\s\-+/]+$")  # word chars, spaces, hyphens, +, /


def _word_count(text: str) -> int:
    return len(text.split())


def _check_variant(v: dict) -> list[str]:
    issues: list[str] = []
    text  = v.get("text", "")
    label = v.get("label", "")

    wc = _word_count(text)
    if wc < 10:
        issues.append(f"[words] too short: {wc} words")
    elif wc > 150:
        issues.append(f"[words] too long: {wc} words")

    if "[Your Name]" not in text:
        issues.append("[name] missing [Your Name] sign-off")

    if _MARKDOWN_RE.search(text):
        issues.append(f"[no-md] markdown artifact: {_MARKDOWN_RE.search(text).group()!r}")

    first_line = text.lstrip().split("\n")[0]
    if _AI_FILLER_RE.match(first_line.strip()):
        issues.append(f"[no-ai] starts with AI filler: {first_line[:40]!r}")

    if "Subject:" in text:
        issues.append("[no-subj] reply body contains 'Subject:' header")

    label_words = label.strip().split()
    if len(label_words) == 0:
        issues.append("[label] empty label")
    elif len(label_words) > 5:
        issues.append(f"[label] too long: {label!r}")
    elif not _LABEL_RE.match(label):
        issues.append(f"[label] invalid chars: {label!r}")

    return issues


# ── Test emails ──────────────────────────────────────────────────────────────

EMAILS = [
    {
        "id": "Q01",
        "subject": "Q3 planning session - Tuesday 3 PM",
        "body": (
            "Hi, we're holding the Q3 planning session on Tuesday at 3 PM in Room 4B. "
            "Please confirm your attendance by Monday noon. "
            "We'll be covering roadmap priorities, headcount, and budget allocation for the quarter."
        ),
        "category": "meeting",
        "priority": "normal",
        "reply_needed": True,
    },
    {
        "id": "Q02",
        "subject": "Security audit report - review by Thursday",
        "body": (
            "The external security audit report is ready. I need your team to review section 3 "
            "(API authentication) and section 7 (data retention) by Thursday EOD. "
            "Please mark up any findings that require immediate remediation."
        ),
        "category": "task",
        "priority": "high",
        "reply_needed": True,
    },
    {
        "id": "Q03",
        "subject": "Partnership proposal — exclusive distribution rights",
        "body": (
            "Dear team, we are pleased to present our partnership proposal for exclusive distribution "
            "rights in the EMEA region. The proposal includes a minimum purchase commitment of $500K "
            "annually, co-marketing support, and dedicated account management. "
            "We would appreciate your response by August 1."
        ),
        "category": "inquiry",
        "priority": "normal",
        "reply_needed": True,
    },
    {
        "id": "Q04",
        "subject": "Platform outage — customers impacted",
        "body": (
            "URGENT: Our platform has been down for 90 minutes. "
            "Approximately 2,000 customers are affected. "
            "Engineering has identified a database connection pool issue and is working on a fix. "
            "We need executive sign-off to trigger the emergency maintenance window."
        ),
        "category": "complaint",
        "priority": "high",
        "reply_needed": True,
    },
    {
        "id": "Q05",
        "subject": "Welcome to CloudSync — account created",
        "body": (
            "Hello! Your CloudSync account has been created. "
            "Username: john.doe@example.com. "
            "You can log in at cloudsync.io. No action required."
        ),
        "category": "update",
        "priority": "low",
        "reply_needed": False,
    },
    {
        "id": "Q06",
        "subject": "Can we catch up this week?",
        "body": (
            "Hey! Haven't talked in a while — would love to catch up over coffee or a quick call "
            "sometime this week if you're free. Let me know what works!"
        ),
        "category": "meeting",
        "priority": "normal",
        "reply_needed": True,
    },
    {
        "id": "Q07",
        "subject": "Invoice #3382 overdue — immediate payment required",
        "body": (
            "Dear Sir/Madam, invoice #3382 for $8,750 was due on June 30 and remains unpaid. "
            "We kindly request immediate payment to avoid service interruption. "
            "Please contact billing@vendor.com if you have any questions."
        ),
        "category": "invoice",
        "priority": "high",
        "reply_needed": True,
    },
    {
        "id": "Q08",
        "subject": "Team lunch next Friday — any dietary requirements?",
        "body": (
            "Hi all! We're organising a team lunch on Friday July 18 at Zuma restaurant at 12:30 PM. "
            "Could everyone reply with any dietary requirements? "
            "Looking forward to celebrating our Q2 launch together!"
        ),
        "category": "update",
        "priority": "low",
        "reply_needed": True,
    },
]

# ── Runner ───────────────────────────────────────────────────────────────────

SEP = "-" * 70

async def run() -> int:
    failures = 0
    print(f"\nRunning reply quality inspection on {len(EMAILS)} emails …")
    print(SEP)

    for em in EMAILS:
        result = await generate_replies(
            em["subject"], em["body"],
            category=em.get("category", ""),
            priority=em.get("priority", "normal"),
        )
        await asyncio.sleep(0.4)

        rn = result.get("reply_needed", True)
        variants = result.get("variants", [])
        expected_rn = em["reply_needed"]

        print(f"\n  {em['id']}  reply_needed={rn}  variants={len(variants)}")

        rn_ok = rn == expected_rn
        if not rn_ok:
            print(f"    FAIL  reply_needed expected={expected_rn} got={rn}")
            failures += 1

        for i, v in enumerate(variants):
            em_issues = _check_variant(v)
            tone_marker = f"[{v.get('tone','?')[:3]}]"
            label = v.get("label", "?")
            wc = _word_count(v.get("text", ""))
            status = "FAIL" if em_issues else "ok  "

            print(f"    {status}  variant {i+1}  {tone_marker}  {label!r:30s}  {wc}w")
            for issue in em_issues:
                print(f"          ✗ {issue}")
                failures += 1

            # Print text for visual review
            for line in v.get("text", "").split("\\n"):
                print(f"          | {line}")

    print(f"\n{SEP}")
    print(f"Total failures: {failures}  (pass threshold: <= 1)")
    if failures <= 1:
        print("QUALITY CHECK PASSED")
    else:
        print("QUALITY CHECK FAILED")
    return failures


if __name__ == "__main__":
    failures = asyncio.run(run())
    sys.exit(0 if failures <= 1 else 1)
