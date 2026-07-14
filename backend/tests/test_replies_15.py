"""
15-email benchmark for reply_agent.generate_replies().

Coverage
--------
  M01-M03  Meeting invites (formal, casual, interview)
  T01-T03  Task requests (report, code review, urgent bug)
  U01-U02  Project updates (no-action, has-question)
  C01-C02  Complaints (external service, internal process)
  A01-A02  Automated / no-reply (shipping, newsletter)
  I01      Invoice received
  E01-E02  Edge cases (FYI with embedded question, multi-topic)

Pass criteria per email:
  - reply_needed matches expected
  - when reply_needed=True: count >= 2
  - all tones are "formal" | "friendly" | "direct"
  - variant labels are non-empty and unique within the email

Overall: >= 13/15 (87%)

Run: python backend/tests/test_replies_15.py
"""
import asyncio
import os
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

VALID_TONES = {"formal", "friendly", "direct"}

EMAILS = [
    # ── Meeting invites ───────────────────────────────────────────────────────
    {
        "id": "M01",
        "subject": "Board presentation prep call - Monday 9 AM",
        "body": (
            "Hi, I've scheduled a prep call for our board presentation on Monday July 14 at 9 AM "
            "in the executive conference room. Attendance is required for all project leads. "
            "Please confirm your attendance by end of day Friday."
        ),
        "sender": "ceo@company.com",
        "category": "meeting",
        "priority": "urgent",
        "expect_reply": True,
        "expect_count_min": 2,
        "expect_labels_include": [],  # just check distinctness
    },
    {
        "id": "M02",
        "subject": "Coffee catch-up this week?",
        "body": (
            "Hey! It's been a while. Would you be free for a quick coffee or video call this week? "
            "I wanted to catch up and hear how the new project is going. Tuesday or Thursday work for me."
        ),
        "sender": "friend@startup.io",
        "category": "meeting",
        "priority": "low",
        "expect_reply": True,
        "expect_count_min": 2,
        "expect_labels_include": [],
    },
    {
        "id": "M03",
        "subject": "Interview scheduled: Senior Engineer - July 17, 2 PM",
        "body": (
            "Dear Applicant, your technical interview for the Senior Engineer role has been confirmed "
            "for Thursday July 17 at 2:00 PM via Google Meet. Please reply to confirm your availability."
        ),
        "sender": "recruiting@company.com",
        "category": "meeting",
        "priority": "high",
        "expect_reply": True,
        "expect_count_min": 2,
        "expect_labels_include": [],
    },

    # ── Task requests ─────────────────────────────────────────────────────────
    {
        "id": "T01",
        "subject": "Q2 report needed by Thursday",
        "body": (
            "Hi, could you please have the Q2 performance report ready by Thursday EOD? "
            "I need it to prepare for the Friday all-hands. Please include the revenue breakdown "
            "and customer satisfaction scores."
        ),
        "sender": "vp@company.com",
        "category": "task",
        "priority": "high",
        "expect_reply": True,
        "expect_count_min": 2,
        "expect_labels_include": [],
    },
    {
        "id": "T02",
        "subject": "Code review request - PR #312",
        "body": (
            "Hey, I've opened PR #312 which refactors the authentication module. "
            "It's a fairly large change so I'd appreciate a thorough review. "
            "No hard deadline, but ideally before the end of the sprint."
        ),
        "sender": "dev@company.com",
        "category": "task",
        "priority": "normal",
        "expect_reply": True,
        "expect_count_min": 2,
        "expect_labels_include": [],
    },
    {
        "id": "T03",
        "subject": "URGENT: Production error 500s on checkout",
        "body": (
            "We're seeing 500 errors on the checkout flow — about 30% of orders are failing. "
            "This started 20 minutes ago. Can you investigate immediately? "
            "The on-call team is waiting on you."
        ),
        "sender": "oncall@company.com",
        "category": "support",
        "priority": "urgent",
        "expect_reply": True,
        "expect_count_min": 2,
        "expect_labels_include": [],
    },

    # ── Project updates ───────────────────────────────────────────────────────
    {
        "id": "U01",
        "subject": "Database migration complete",
        "body": (
            "Hi team, just a heads-up — the database migration to the new cluster completed "
            "successfully at 2 AM. No data loss, all services are healthy. "
            "No action needed from anyone."
        ),
        "sender": "infra@company.com",
        "category": "update",
        "priority": "normal",
        "expect_reply": True,
        "expect_count_min": 2,
        "expect_labels_include": [],
    },
    {
        "id": "U02",
        "subject": "Sprint review summary",
        "body": (
            "Hi, here's a summary of this sprint: we shipped 12/14 planned stories. "
            "The 2 carry-overs are the API rate limiter and the dark mode toggle. "
            "Any thoughts on whether we should prioritize these next sprint?"
        ),
        "sender": "pm@company.com",
        "category": "update",
        "priority": "normal",
        "expect_reply": True,
        "expect_count_min": 2,
        "expect_labels_include": [],
    },

    # ── Complaints ────────────────────────────────────────────────────────────
    {
        "id": "C01",
        "subject": "Your platform lost our data",
        "body": (
            "This is unacceptable. We exported our customer list last week and the file was corrupted. "
            "We've now lost 500 customer records. This is a serious data loss incident and I expect "
            "a full explanation and immediate recovery assistance."
        ),
        "sender": "cto@client.com",
        "category": "complaint",
        "priority": "urgent",
        "expect_reply": True,
        "expect_count_min": 2,
        "expect_labels_include": [],
    },
    {
        "id": "C02",
        "subject": "The sprint planning process is broken",
        "body": (
            "I've raised this before but sprint planning continues to run over 3 hours every two weeks. "
            "It's killing team morale and productivity. We need to fix this process. "
            "Can we discuss a better approach?"
        ),
        "sender": "engineer@company.com",
        "category": "complaint",
        "priority": "normal",
        "expect_reply": True,
        "expect_count_min": 2,
        "expect_labels_include": [],
    },

    # ── Automated / no-reply ──────────────────────────────────────────────────
    {
        "id": "A01",
        "subject": "Your subscription has been renewed",
        "body": (
            "Hi, your annual subscription to MailMind Pro has been automatically renewed. "
            "Amount charged: $199.00. Your next renewal date is July 13, 2027. "
            "No action required."
        ),
        "sender": "billing@mailmind.com",
        "category": "invoice",
        "priority": "low",
        "expect_reply": False,
        "expect_count_min": 0,
        "expect_labels_include": [],
    },
    {
        "id": "A02",
        "subject": "The weekly newsletter — top stories this week",
        "body": (
            "Hi there! Here are the top stories from our community this week:\n"
            "1. How we scaled to 10M users\n"
            "2. The future of async communication\n"
            "3. Why your team needs a writing culture\n\n"
            "Click to read more. Unsubscribe at any time."
        ),
        "sender": "newsletter@publication.com",
        "category": "spam",
        "priority": "low",
        "expect_reply": False,
        "expect_count_min": 0,
        "expect_labels_include": [],
    },

    # ── Invoice ───────────────────────────────────────────────────────────────
    {
        "id": "I01",
        "subject": "Invoice INV-2024-07 for July services",
        "body": (
            "Dear Customer, please find attached invoice INV-2024-07 for $3,200 covering "
            "consulting services provided in July 2024. Payment is due by July 30."
        ),
        "sender": "accounts@consultant.com",
        "category": "invoice",
        "priority": "normal",
        "expect_reply": True,
        "expect_count_min": 2,
        "expect_labels_include": [],
    },

    # ── Edge cases ────────────────────────────────────────────────────────────
    {
        "id": "E01",
        "subject": "FYI - Q3 roadmap finalized",
        "body": (
            "Hi team, just sharing that we've finalized the Q3 product roadmap. "
            "The main themes are performance, integrations, and mobile parity. "
            "You can view the full doc in Notion. "
            "By the way — are you planning to attend the roadmap walkthrough session on Wednesday?"
        ),
        "sender": "product@company.com",
        "category": "update",
        "priority": "normal",
        "expect_reply": True,  # has a question at the end
        "expect_count_min": 2,
        "expect_labels_include": [],
    },
    {
        "id": "E02",
        "subject": "Several things to follow up on",
        "body": (
            "Hi, a few things from our last sync:\n"
            "1. The client wants a revised proposal by Wednesday — can you handle that?\n"
            "2. HR needs your updated emergency contacts form.\n"
            "3. The team lunch is confirmed for Friday at the Italian place.\n\n"
            "Let me know if you have any questions."
        ),
        "sender": "manager@company.com",
        "category": "task",
        "priority": "high",
        "expect_reply": True,
        "expect_count_min": 2,
        "expect_labels_include": [],
    },
]

# ── Runner ────────────────────────────────────────────────────────────────────

def _check(email: dict, result: dict) -> tuple[bool, list[str]]:
    fails = []
    rn = result.get("reply_needed", True)

    if rn != email["expect_reply"]:
        fails.append(f"reply_needed: expected {email['expect_reply']}, got {rn}")

    if email["expect_reply"]:
        count = result.get("count", 0)
        if count < email["expect_count_min"]:
            fails.append(f"count: expected >= {email['expect_count_min']}, got {count}")

        for v in result.get("variants", []):
            if v["tone"] not in VALID_TONES:
                fails.append(f"invalid tone '{v['tone']}'")

        labels = [v["label"] for v in result.get("variants", [])]
        if len(labels) != len(set(labels)):
            fails.append(f"duplicate labels: {labels}")

    return len(fails) == 0, fails


async def run_benchmark() -> None:
    passed = 0
    total  = len(EMAILS)
    failures: list[str] = []

    print(f"Running {total}-email reply benchmark...")
    print("-" * 64)

    for email in EMAILS:
        eid = email["id"]
        try:
            result = await generate_replies(
                subject=email["subject"],
                body=email["body"],
                sender=email.get("sender", ""),
                category=email.get("category", ""),
                priority=email.get("priority", "normal"),
            )
        except Exception as exc:
            print(f"  {eid}  ERROR  {exc}")
            failures.append(f"{eid}: exception — {exc}")
            continue

        ok, fails = _check(email, result)
        rn = result.get("reply_needed", True)
        n  = result.get("count", 0)

        # Build compact variant summary
        var_str = ""
        if n > 0:
            var_str = "  " + " | ".join(
                f"[{v['tone'][:3]}] {v['label']}" for v in result["variants"]
            )

        status = "PASS" if ok else "FAIL"
        rn_str = "reply" if rn else "no-reply"
        print(f"  {eid}  {rn_str}  n={n}  {status}{var_str}")

        if fails:
            for f in fails:
                print(f"         !! {f}")
            failures.append(f"{eid}: " + " | ".join(fails))
        else:
            passed += 1

        await asyncio.sleep(0.5)

    print("-" * 64)
    pct = int(passed / total * 100)
    print(f"Result: {passed}/{total} = {pct}%  (target >= 13/15 = 87%)")

    if passed >= 13:
        print("BENCHMARK PASSED")
        sys.exit(0)
    else:
        print("BENCHMARK FAILED")
        for line in failures:
            print(f"  - {line}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_benchmark())
