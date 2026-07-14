"""
Manual accuracy test for the classification + priority agent.
Run from backend/ with:  python -m tests.test_classification
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.classification_agent import classify_email

# ── Ground-truth test set (20 emails) ───────────────────────────────────────
# Each entry: (subject, body, expected_category, expected_priority)

TEST_EMAILS: list[tuple[str, str, str, str]] = [
    # ── meeting ──────────────────────────────────────────────────────────────
    (
        "Team sync – Thursday 2pm",
        "Hi everyone, let's meet Thursday at 2pm to go over the sprint goals. "
        "Please block your calendar and bring your status updates.",
        "meeting", "normal",
    ),
    (
        "URGENT: Executive all-hands moved to TODAY 10am",
        "The all-hands has been rescheduled to today at 10am in Conference Room A. "
        "Attendance is mandatory. Please confirm your presence immediately.",
        "meeting", "urgent",
    ),
    # ── complaint ────────────────────────────────────────────────────────────
    (
        "Extremely disappointed with your service",
        "I have been a customer for 3 years and this is the worst experience I've had. "
        "My order arrived damaged and customer service hasn't responded in a week. "
        "I expect a full refund within 24 hours.",
        "complaint", "high",
    ),
    (
        "I am filing a lawsuit this afternoon",
        "You have ignored my complaints for 4 weeks. My attorney has prepared a lawsuit "
        "which I will file by 3pm today unless I receive a full refund and written apology "
        "within the next 2 hours.",
        "complaint", "urgent",
    ),
    # ── job ──────────────────────────────────────────────────────────────────
    (
        "Your application has been received – Senior Backend Engineer",
        "Thank you for applying to the Senior Backend Engineer position at Acme Corp. "
        "We will review your application and get back to you within 5 business days.",
        "job", "normal",
    ),
    (
        "Interview tomorrow at 9am – please confirm by EOD",
        "We'd like to interview you for the Product Manager role tomorrow at 9am. "
        "Please confirm your attendance by end of today or we will offer the slot "
        "to another candidate.",
        "job", "urgent",
    ),
    (
        "Offer letter attached – expires in 48 hours",
        "Congratulations! We are pleased to extend an offer for the Staff Engineer role. "
        "Please review and sign the attached offer letter. The offer expires in 48 hours.",
        "job", "high",
    ),
    # ── update ───────────────────────────────────────────────────────────────
    (
        "Monthly company newsletter – June",
        "Welcome to the June edition of our company newsletter! This month we celebrated "
        "our 10th anniversary, launched two new products, and welcomed 50 new team members.",
        "update", "low",
    ),
    (
        "Sprint 22 status report",
        "Sprint 22 update: Auth service is 90% complete. Payment module is blocked on "
        "the third-party API contract. Dashboard shipped to staging. Next review is Friday.",
        "update", "normal",
    ),
    (
        "CRITICAL: Zero-day vulnerability in OpenSSL – patch by midnight",
        "A critical zero-day (CVE-2024-1234) affecting OpenSSL has been disclosed. "
        "All production servers must be patched before midnight tonight. "
        "Unpatched systems will be taken offline.",
        "update", "urgent",
    ),
    # ── invoice ──────────────────────────────────────────────────────────────
    (
        "Invoice #INV-0892 – due in 30 days",
        "Please find attached invoice #INV-0892 for $3,400 for web development services "
        "rendered in June. Payment is due by August 1st via bank transfer.",
        "invoice", "normal",
    ),
    (
        "FINAL NOTICE: Invoice overdue – collections referral in 48 hours",
        "Invoice #INV-0741 ($6,200) is now 45 days overdue. This is your final notice. "
        "If payment is not received within 48 hours, your account will be referred to "
        "our collections agency and a lien may be placed.",
        "invoice", "urgent",
    ),
    (
        "Invoice #INV-0950 overdue by 15 days – late fee applied",
        "Invoice #INV-0950 ($1,800) was due on June 15th and remains unpaid. "
        "A 5% late fee ($90) has been added. Please settle this within the next 7 days "
        "to avoid further charges.",
        "invoice", "high",
    ),
    # ── support ──────────────────────────────────────────────────────────────
    (
        "How do I export my data to CSV?",
        "Hi support team, I'm trying to export my account data to a CSV file but I "
        "can't find the option in the settings menu. Could you point me in the right direction?",
        "support", "normal",
    ),
    (
        "CRITICAL: Production database unreachable – all users affected",
        "Our production PostgreSQL cluster has been unreachable since 08:30 UTC. "
        "All user logins are failing. Estimated revenue impact: $15,000 per minute. "
        "Please escalate to on-call immediately.",
        "support", "urgent",
    ),
    (
        "Payment checkout broken – users can't complete purchases",
        "Since the deployment at 14:00, the checkout page throws a 500 error for all users. "
        "We're losing sales. Please investigate ASAP.",
        "support", "high",
    ),
    # ── social ───────────────────────────────────────────────────────────────
    (
        "Happy birthday! 🎂",
        "Hey! Just wanted to wish you a very happy birthday. Hope you have an amazing day "
        "celebrating with family and friends!",
        "social", "low",
    ),
    (
        "Great meeting you at the conference!",
        "Hi, it was really great connecting with you at the TechConf summit yesterday. "
        "I'd love to keep in touch. Let's grab coffee sometime next month if you're free.",
        "social", "low",
    ),
    # ── spam ─────────────────────────────────────────────────────────────────
    (
        "You've been selected! Claim your $1,000 Amazon gift card NOW",
        "Congratulations! You are our lucky winner this week. Click the link below to "
        "claim your $1,000 Amazon gift card before it expires. Act fast – only 3 left!",
        "spam", "low",
    ),
    (
        "Make $5,000/week working from home – limited spots available",
        "Are you tired of the 9-to-5? Join thousands of people earning $5,000 a week from home. "
        "No experience needed. Click here to secure your spot before it's gone!",
        "spam", "low",
    ),
]

# ── Runner ───────────────────────────────────────────────────────────────────

BOLD  = ""
GREEN = ""
RED   = ""
RESET = ""
DIM   = ""


async def run_tests() -> None:
    cat_correct = 0
    pri_correct = 0
    both_correct = 0
    total = len(TEST_EMAILS)

    header = (
        f"{'#':<3}  {'Subject':<42}  "
        f"{'Expected Cat':<12} {'Got Cat':<12}  "
        f"{'Exp Pri':<8} {'Got Pri':<8}  "
        f"{'Cat':^4} {'Pri':^4} {'Conf':>5}"
    )
    print(f"\n{BOLD}{header}{RESET}")
    print("-" * len(header))

    for i, (subject, body, exp_cat, exp_pri) in enumerate(TEST_EMAILS, 1):
        await asyncio.sleep(0.5)  # stay within Groq per-minute token limit
        result = await classify_email(subject, body)
        got_cat = result["category"]
        got_pri = result["priority"]
        conf    = result["confidence"]

        cat_ok  = got_cat == exp_cat
        pri_ok  = got_pri == exp_pri
        both_ok = cat_ok and pri_ok

        if cat_ok:
            cat_correct += 1
        if pri_ok:
            pri_correct += 1
        if both_ok:
            both_correct += 1

        cat_mark  = "OK" if cat_ok  else "FAIL"
        pri_mark  = "OK" if pri_ok  else "FAIL"

        short_subj = subject[:40] + ".." if len(subject) > 40 else subject
        short_subj = short_subj.encode("ascii", "replace").decode("ascii")
        got_cat_str = got_cat
        got_pri_str = got_pri

        print(
            f"{i:<3}  {short_subj:<42}  "
            f"{exp_cat:<12} {got_cat_str:<12}  "
            f"{exp_pri:<8} {got_pri_str:<8}  "
            f"{cat_mark:^4} {pri_mark:^4} {conf:>5.2f}"
        )

    print("-" * len(header))
    print(f"\n{BOLD}Results ({total} emails){RESET}")
    print(f"  Category accuracy : {cat_correct}/{total}  = {cat_correct/total*100:.1f}%")
    print(f"  Priority accuracy : {pri_correct}/{total}  = {pri_correct/total*100:.1f}%")
    print(f"  Both correct      : {both_correct}/{total} = {both_correct/total*100:.1f}%\n")


if __name__ == "__main__":
    asyncio.run(run_tests())
