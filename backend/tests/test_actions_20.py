"""
20-email benchmark for action_agent.extract_actions().

Coverage
--------
  M01-M05  Meeting detection (formal, casual, recurring, interview, team lunch)
  D01-D04  Deadline detection (single, multiple, ASAP, absolute)
  T01-T05  Task extraction (single, review, multi, sender-task, follow-up)
  X01-X03  Mixed (meeting+task, meeting+deadline, all three)
  C01-C03  Clean emails (no actions expected)

Pass criteria per email: all expected bool flags match actual flags.
Overall: >= 17/20 correct.

Run: python backend/tests/test_actions_20.py
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, "backend")

# Load .env from backend/ so OPENAI_API_KEY / GROQ_API_KEY is available
_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

from app.action_agent import extract_actions

# ── Test corpus ───────────────────────────────────────────────────────────────

EMAILS = [
    # ── Meeting detection ─────────────────────────────────────────────────────
    {
        "id": "M01",
        "subject": "Q3 Strategy Meeting - Thursday at 2 PM",
        "body": (
            "Hi team,\n\n"
            "You are invited to the Q3 Strategy Meeting on Thursday, July 17 at 2:00 PM in "
            "Conference Room B. The session will run for approximately 90 minutes.\n\n"
            "Agenda:\n"
            "- Q2 performance review\n"
            "- Q3 goals and OKRs\n"
            "- Budget allocation\n\n"
            "Please confirm your attendance by Wednesday. Looking forward to seeing everyone.\n\n"
            "Best,\nSarah"
        ),
        "sender": "sarah@company.com",
        # "confirm your attendance by Wednesday" is a genuine task
        "expect": {"has_meeting": True, "has_deadlines": True, "has_tasks": True},
    },
    {
        "id": "M02",
        "subject": "Catch up this week?",
        "body": (
            "Hey,\n\n"
            "Are you free for a quick call sometime this week? I want to discuss the "
            "onboarding process. Tuesday afternoon or Wednesday morning work best for me.\n\n"
            "Let me know!\nMike"
        ),
        "sender": "mike@company.com",
        # "Let me know!" is an implicit task (reply to confirm/schedule)
        "expect": {"has_meeting": True, "has_deadlines": False, "has_tasks": True},
    },
    {
        "id": "M03",
        "subject": "Weekly Sync - Every Monday 10 AM Zoom",
        "body": (
            "Hi everyone,\n\n"
            "This is a reminder that our Weekly Engineering Sync takes place every Monday at "
            "10:00 AM via Zoom. Join link: zoom.us/j/123456789.\n\n"
            "Duration: 30 minutes. Bring your blockers and updates.\n\n"
            "First session starts this Monday, July 14.\n\nThanks,\nJen"
        ),
        "sender": "jen@company.com",
        "expect": {"has_meeting": True, "has_deadlines": False, "has_tasks": False},
    },
    {
        "id": "M04",
        "subject": "Interview Scheduled: Software Engineer - July 16, 2:00 PM",
        "body": (
            "Dear Applicant,\n\n"
            "Your interview for the Software Engineer position has been scheduled:\n\n"
            "Date: Wednesday, July 16\n"
            "Time: 2:00 PM - 3:00 PM\n"
            "Format: Video call via Google Meet\n"
            "Interviewer: David Chen, Engineering Manager\n\n"
            "Please confirm your availability by replying to this email.\n\n"
            "Best regards,\nHR Team"
        ),
        "sender": "hr@company.com",
        "expect": {"has_meeting": True, "has_deadlines": False, "has_tasks": True},
    },
    {
        "id": "M05",
        "subject": "Project kickoff - Monday July 21",
        "body": (
            "Team,\n\n"
            "Our project kickoff is scheduled for Monday July 21 at 9 AM in the main boardroom. "
            "All stakeholders are expected to attend. The kickoff will cover project scope, "
            "timelines, and team responsibilities.\n\n"
            "Please review the attached brief before the meeting.\n\nRegards,\nPM"
        ),
        "sender": "pm@company.com",
        "expect": {"has_meeting": True, "has_deadlines": False, "has_tasks": True},
    },

    # ── Deadline detection ────────────────────────────────────────────────────
    {
        "id": "D01",
        "subject": "Report submission",
        "body": (
            "Hi,\n\n"
            "A friendly reminder that the Q2 performance report is due by Friday EOD. "
            "Please ensure all sections are complete before submitting.\n\nThanks"
        ),
        "sender": "boss@company.com",
        "expect": {"has_meeting": False, "has_deadlines": True, "has_tasks": True},
    },
    {
        "id": "D02",
        "subject": "Conference submission deadlines",
        "body": (
            "Dear Author,\n\n"
            "Please note the following deadlines for the upcoming conference:\n\n"
            "- Abstract submission: by August 1\n"
            "- Full paper: by August 15\n"
            "- Camera-ready copy: due September 1\n\n"
            "Late submissions will not be considered.\n\nBest,\nPC Chair"
        ),
        "sender": "chair@conference.org",
        "expect": {"has_meeting": False, "has_deadlines": True, "has_tasks": False},
    },
    {
        "id": "D03",
        "subject": "URGENT: Server credentials needed ASAP",
        "body": (
            "Hi,\n\n"
            "We have a production incident and need the staging server credentials ASAP. "
            "Please send them as soon as you can — every minute counts right now.\n\n"
            "Thanks,\nDevOps"
        ),
        "sender": "devops@company.com",
        "expect": {"has_meeting": False, "has_deadlines": True, "has_tasks": True},
    },
    {
        "id": "D04",
        "subject": "Contract renewal deadline",
        "body": (
            "Dear Partner,\n\n"
            "This is a reminder that your service contract expires on July 31. "
            "To renew without interruption, we must receive your signed agreement "
            "no later than next Monday.\n\nPlease don't hesitate to contact us.\n\nBest"
        ),
        "sender": "contracts@vendor.com",
        # "we must receive your signed agreement" — recipient needs to sign/return
        "expect": {"has_meeting": False, "has_deadlines": True, "has_tasks": True},
    },

    # ── Task extraction ───────────────────────────────────────────────────────
    {
        "id": "T01",
        "subject": "Invoice for last month",
        "body": (
            "Hi,\n\nCould you please send me the invoice for services rendered in June? "
            "I need it to process the payment by end of this week.\n\nThanks,\nAlex"
        ),
        "sender": "alex@client.com",
        "expect": {"has_meeting": False, "has_deadlines": True, "has_tasks": True},
        "expect_task_assignee": "me",
    },
    {
        "id": "T02",
        "subject": "PR Review Request",
        "body": (
            "Hey,\n\n"
            "I've opened PR #247 for the new authentication module. Could you review it "
            "when you have a moment? No hard deadline, but sooner is better so we can "
            "merge before the release.\n\nThanks,\nDev"
        ),
        "sender": "dev@company.com",
        "expect": {"has_meeting": False, "has_deadlines": False, "has_tasks": True},
        "expect_task_assignee": "me",
    },
    {
        "id": "T03",
        "subject": "Two quick things",
        "body": (
            "Hi,\n\n"
            "Two quick things I need from you:\n\n"
            "1) Please update the README with the new API endpoints.\n"
            "2) Can you also add me to the Slack channel #backend-team?\n\n"
            "Both are pretty urgent. Thanks!"
        ),
        "sender": "lead@company.com",
        "expect": {"has_meeting": False, "has_deadlines": False, "has_tasks": True},
        "expect_task_assignee": "me",
        "expect_task_count_min": 2,
    },
    {
        "id": "T04",
        "subject": "Slides coming your way",
        "body": (
            "Hi,\n\n"
            "I've finished the first draft of the presentation slides. "
            "I'll send them over to you by tomorrow morning so you can review before the call. "
            "Let me know if you'd like any sections rearranged.\n\nBest,\nJane"
        ),
        "sender": "jane@company.com",
        "expect": {"has_meeting": False, "has_deadlines": True, "has_tasks": True},
    },
    {
        "id": "T05",
        "subject": "Meeting follow-up action items",
        "body": (
            "Hi team,\n\n"
            "Thanks for joining today's product review. Here are the action items:\n\n"
            "- [You] Schedule a demo with the client by next week\n"
            "- [You] Update the product spec document with today's changes\n"
            "- [Sarah] Prepare cost estimates by Thursday\n\n"
            "Let me know if I missed anything.\n\nBest,\nPM"
        ),
        "sender": "pm@company.com",
        "expect": {"has_meeting": False, "has_deadlines": True, "has_tasks": True},
        "expect_task_assignee": "me",
        "expect_task_count_min": 2,
    },

    # ── Mixed emails ──────────────────────────────────────────────────────────
    {
        "id": "X01",
        "subject": "Design review Thursday - please prepare mockups",
        "body": (
            "Hi,\n\n"
            "We're holding a design review on Thursday at 3 PM in the design room. "
            "Please prepare your latest mockups and be ready to walk through the user flows.\n\n"
            "Looking forward to it!\nCarlos"
        ),
        "sender": "carlos@company.com",
        "expect": {"has_meeting": True, "has_deadlines": False, "has_tasks": True},
    },
    {
        "id": "X02",
        "subject": "Kickoff meeting July 20 - agenda due July 18",
        "body": (
            "Team,\n\n"
            "Project kickoff is set for Monday July 20 at 10 AM via Zoom. "
            "Please submit your agenda items by Friday July 18 so I can compile the final agenda.\n\n"
            "The session will be 2 hours. All team leads are required to attend.\n\nThanks"
        ),
        "sender": "pm@company.com",
        "expect": {"has_meeting": True, "has_deadlines": True, "has_tasks": True},
    },
    {
        "id": "X03",
        "subject": "Sales call Wednesday + follow-up report due Friday",
        "body": (
            "Hi,\n\n"
            "We have a sales call with Acme Corp on Wednesday July 16 at 11 AM. "
            "The call should take about 45 minutes. Please prepare the Q2 pricing deck beforehand.\n\n"
            "After the call, a follow-up report is due by Friday EOD — please send it to "
            "the sales director.\n\nThanks,\nManager"
        ),
        "sender": "manager@company.com",
        "expect": {"has_meeting": True, "has_deadlines": True, "has_tasks": True},
    },

    # ── Clean emails (no actions expected) ────────────────────────────────────
    {
        "id": "C01",
        "subject": "Thank you!",
        "body": (
            "Hi,\n\n"
            "Just wanted to say thank you for your help with the project last week. "
            "Your contributions made a real difference and the client was very happy.\n\n"
            "Appreciate you!\nBoss"
        ),
        "sender": "boss@company.com",
        "expect": {"has_meeting": False, "has_deadlines": False, "has_tasks": False},
    },
    {
        "id": "C02",
        "subject": "Office closed Monday July 14",
        "body": (
            "Hi all,\n\n"
            "FYI — the office will be closed on Monday July 14 due to a public holiday. "
            "Normal operations resume on Tuesday. No action is required.\n\nAdmin Team"
        ),
        "sender": "admin@company.com",
        "expect": {"has_meeting": False, "has_deadlines": False, "has_tasks": False},
    },
    {
        "id": "C03",
        "subject": "Your June invoice - #INV-2024-06",
        "body": (
            "Dear Customer,\n\n"
            "Your invoice for June 2024 is now available. Total: $149.00.\n\n"
            "This is an automated notification. Payment will be automatically collected "
            "from your card on file in 3 days. No action is required.\n\nBilling Team"
        ),
        "sender": "billing@saas.com",
        "expect": {"has_meeting": False, "has_deadlines": False, "has_tasks": False},
    },
]

# ── Runner ────────────────────────────────────────────────────────────────────

def _check(email: dict, result: dict) -> tuple[bool, list[str]]:
    expect = email["expect"]
    failures = []

    for flag in ("has_meeting", "has_deadlines", "has_tasks"):
        got = result[flag]
        want = expect[flag]
        if got != want:
            failures.append(f"{flag}: expected {want}, got {got}")

    # Bonus checks (do not fail the email, just report)
    if "expect_task_assignee" in email and result["has_tasks"]:
        assignee = email["expect_task_assignee"]
        found = any(t["assignee"] == assignee for t in result["tasks"])
        if not found:
            failures.append(
                f"no task with assignee='{assignee}' (got: "
                f"{[t['assignee'] for t in result['tasks']]})"
            )

    if "expect_task_count_min" in email:
        min_tasks = email["expect_task_count_min"]
        got_count = len(result["tasks"])
        if got_count < min_tasks:
            failures.append(
                f"expected >= {min_tasks} tasks, got {got_count}"
            )

    return len(failures) == 0, failures


async def run_benchmark() -> None:
    passed = 0
    total = len(EMAILS)
    failures_summary: list[str] = []

    print(f"Running {total}-email action extraction benchmark...")
    print("-" * 60)

    for email in EMAILS:
        eid = email["id"]
        try:
            result = await extract_actions(
                subject=email["subject"],
                body=email["body"],
                sender=email.get("sender", ""),
            )
        except Exception as exc:
            print(f"  {eid}  ERROR  {exc}")
            failures_summary.append(f"{eid}: exception — {exc}")
            continue

        ok, fails = _check(email, result)

        # Build status line
        m = "M" if result["has_meeting"] else "."
        d = "D" if result["has_deadlines"] else "."
        t = "T" if result["has_tasks"] else "."
        tasks_detail = ""
        if result["tasks"]:
            tasks_detail = f"  tasks({len(result['tasks'])}): " + ", ".join(
                f"{tt['assignee']}:{tt['title'][:20]}" for tt in result["tasks"][:3]
            )
        mtg_detail = ""
        if result["has_meeting"]:
            m_data = result["meeting"]
            mtg_detail = f"  mtg: {m_data.get('title','?')[:30]} @ {m_data.get('date_str','?')[:20]}"

        status = "PASS" if ok else "FAIL"
        print(f"  {eid}  [{m}{d}{t}]  {status}{mtg_detail}{tasks_detail}")

        if fails:
            for f in fails:
                print(f"         !! {f}")
            failures_summary.append(f"{eid}: " + " | ".join(fails))

        if ok:
            passed += 1

        await asyncio.sleep(0.5)  # rate limit buffer

    print("-" * 60)
    pct = int(passed / total * 100)
    print(f"Result: {passed}/{total} = {pct}%  (target >= 17/20 = 85%)")

    if passed >= 17:
        print("BENCHMARK PASSED")
        sys.exit(0)
    else:
        print("BENCHMARK FAILED")
        print("\nFailed emails:")
        for line in failures_summary:
            print(f"  - {line}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_benchmark())
