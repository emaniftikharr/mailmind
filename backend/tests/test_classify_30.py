"""
Classification accuracy — 30-email final benchmark.

Coverage (5 emails per priority level, all 8 categories represented)
----------------------------------------------------------------------
  URGENT  U01-U07  — same-day irreversible consequence
  HIGH    H01-H06  — 24-48h window, serious consequence
  NORMAL  N01-N09  — act-this-week standard correspondence
  LOW     L01-L08  — no action, newsletters, social, spam

Edge cases
----------
  • Security advisory (update, not support)
  • Spear-phish-looking IT email (not spam — update or support)
  • Ambiguous meeting vs. social
  • Invoice urgent vs. high
  • Job offer urgent vs. high

Pass threshold: >= 27/30 (90%)

Run: python backend/tests/test_classify_30.py
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

from app.classification_agent import classify_email

EMAILS = [
    # ── URGENT ────────────────────────────────────────────────────────────────
    {
        "id": "U01", "exp_category": "support", "exp_priority": "urgent",
        "subject": "CRITICAL: Production database down — ALL users locked out",
        "body": (
            "Our PostgreSQL primary cluster failed at 09:15 UTC. "
            "All user logins are failing. Revenue impact is $22k/minute. "
            "Engineers are on the call. ETA unknown. Exec sign-off needed to trigger DR failover."
        ),
    },
    {
        "id": "U02", "exp_category": "complaint", "exp_priority": "urgent",
        "subject": "Filing lawsuit TODAY at 3 PM — last chance to respond",
        "body": (
            "My attorney will file the lawsuit at 3 PM unless I receive a full refund of $4,200 "
            "within the next two hours. This is my final notice before legal action."
        ),
    },
    {
        "id": "U03", "exp_category": "job", "exp_priority": "urgent",
        "subject": "Offer letter — must countersign by 5 PM today",
        "body": (
            "Congratulations! Attached is your offer letter for Senior Engineer. "
            "The offer is valid until 5 PM today. If we do not receive your countersignature "
            "by EOD, the position will be offered to our next candidate."
        ),
    },
    {
        "id": "U04", "exp_category": "invoice", "exp_priority": "urgent",
        "subject": "FINAL NOTICE: Invoice #4421 — collections referral in 2 hours",
        "body": (
            "Invoice #4421 for $11,500 is 60 days overdue. "
            "Our collections agency will receive this account within 2 hours unless "
            "full payment is made immediately. Please call us now to resolve."
        ),
    },
    {
        "id": "U05", "exp_category": "update", "exp_priority": "urgent",
        "subject": "CRITICAL security patch CVE-2025-3821 — apply before midnight",
        "body": (
            "A zero-day in libssl has been publicly disclosed. Active exploitation confirmed. "
            "All production systems must apply patch v3.1.4 before midnight tonight "
            "to avoid mandatory compliance reporting under SOC 2."
        ),
    },
    {
        "id": "U06", "exp_category": "job", "exp_priority": "urgent",
        "subject": "Interview confirmation required by EOD — slot forfeits at 6 PM",
        "body": (
            "Please confirm your attendance for tomorrow's interview by 6 PM today. "
            "If we do not hear from you, we will offer the slot to our next candidate. "
            "The panel has been arranged around your availability."
        ),
    },
    {
        "id": "U07", "exp_category": "support", "exp_priority": "urgent",
        "subject": "Checkout page down — cannot process payments since 2 AM",
        "body": (
            "Our entire checkout flow has been broken since the 2 AM deployment. "
            "No orders are being processed. Estimated loss: $8k/hour. "
            "Need a hotfix or rollback decision immediately."
        ),
    },
    # ── HIGH ──────────────────────────────────────────────────────────────────
    {
        "id": "H01", "exp_category": "complaint", "exp_priority": "high",
        "subject": "Refund demand — I expect resolution within 24 hours",
        "body": (
            "My laptop arrived with a cracked screen. I have been a customer for 5 years. "
            "I demand a full refund or replacement within 24 hours or I will dispute "
            "the charge with my bank."
        ),
    },
    {
        "id": "H02", "exp_category": "job", "exp_priority": "high",
        "subject": "Offer letter attached — expires 48 hours from now",
        "body": (
            "We are thrilled to extend you an offer for Principal Engineer. "
            "Please review the attached letter and return it signed within 48 hours. "
            "We look forward to having you on the team."
        ),
    },
    {
        "id": "H03", "exp_category": "invoice", "exp_priority": "high",
        "subject": "Invoice overdue 30 days — service suspension in 48h",
        "body": (
            "Invoice #882 for $3,200 is now 30 days overdue. "
            "If payment is not received within 48 hours, your API access will be suspended. "
            "Please remit payment or contact us to discuss a payment plan."
        ),
    },
    {
        "id": "H04", "exp_category": "support", "exp_priority": "high",
        "subject": "Payments module throwing 500 errors — checkout degraded",
        "body": (
            "Since the 16:00 deploy, the Stripe webhook handler is returning 500. "
            "Roughly 20% of checkout attempts are failing. "
            "Core functionality is up but we are losing transactions."
        ),
    },
    {
        "id": "H05", "exp_category": "update", "exp_priority": "high",
        "subject": "Database migration scheduled — 2-hour downtime window Thursday",
        "body": (
            "We are migrating the orders database to the new cluster on Thursday between "
            "02:00 and 04:00 UTC. The API will be read-only during this window. "
            "Please plan your deployments accordingly and confirm receipt."
        ),
    },
    {
        "id": "H06", "exp_category": "meeting", "exp_priority": "high",
        "subject": "Board presentation — requires your input by tomorrow noon",
        "body": (
            "The board deck is due to the directors by Thursday morning. "
            "I need your slides and the Q3 metrics by tomorrow noon so I can consolidate. "
            "This presentation cannot go out without your section — please prioritise."
        ),
    },
    # ── NORMAL ────────────────────────────────────────────────────────────────
    {
        "id": "N01", "exp_category": "meeting", "exp_priority": "normal",
        "subject": "Q3 planning sync — Thursday 2 PM",
        "body": (
            "Hi team, I have booked a Q3 planning session for Thursday at 2 PM in Room 4B. "
            "Agenda: roadmap, headcount, and budget. Calendar invite to follow."
        ),
    },
    {
        "id": "N02", "exp_category": "invoice", "exp_priority": "normal",
        "subject": "Invoice INV-0892 due August 1st",
        "body": (
            "Please find attached invoice #INV-0892 for $3,400 for web development services "
            "completed in July. Payment is due by August 1st. Thank you."
        ),
    },
    {
        "id": "N03", "exp_category": "support", "exp_priority": "normal",
        "subject": "Bug report: export CSV crashes for datasets > 10k rows",
        "body": (
            "Hi support team, I have found a bug. When I export a CSV with more than 10,000 rows, "
            "the page throws a JavaScript error and the download does not start. "
            "This is blocking my monthly reporting workflow."
        ),
    },
    {
        "id": "N04", "exp_category": "job", "exp_priority": "normal",
        "subject": "Application received — Software Engineer position",
        "body": (
            "Thank you for applying for the Software Engineer role at TechCo. "
            "We have received your application and will be in touch within 5–7 business days "
            "to let you know if you have been selected for a screening call."
        ),
    },
    {
        "id": "N05", "exp_category": "complaint", "exp_priority": "normal",
        "subject": "Disappointed with recent service quality",
        "body": (
            "I have been a customer for two years and the quality of support responses has declined. "
            "My last three tickets took over a week to resolve. "
            "I wanted to bring this to your attention before escalating further."
        ),
    },
    {
        "id": "N06", "exp_category": "update", "exp_priority": "normal",
        "subject": "Product roadmap update — Q3 priorities",
        "body": (
            "Team, sharing the Q3 roadmap priorities following last week's strategy session. "
            "We are focusing on performance improvements, the new dashboard, and API v2. "
            "Detailed specs will follow next week. No action required."
        ),
    },
    {
        "id": "N07", "exp_category": "update", "exp_priority": "normal",
        "subject": "Security advisory: npm package 'lodash' vulnerability CVE-2025-1122",
        "body": (
            "A path traversal vulnerability has been disclosed in lodash <4.17.22. "
            "Please update your dependencies. This is an advisory — no active exploitation "
            "has been detected in our environment."
        ),
    },
    {
        "id": "N08", "exp_category": "meeting", "exp_priority": "normal",
        "subject": "1:1 reschedule request — can we move to Friday?",
        "body": (
            "Hi, I have a conflict on Thursday morning. "
            "Would it be possible to move our 1:1 to Friday at 10 AM instead? "
            "Let me know and I will update the calendar invite."
        ),
    },
    {
        "id": "N09", "exp_category": "invoice", "exp_priority": "normal",
        "subject": "Stripe invoice for August — $249.00",
        "body": (
            "Hi, your Stripe invoice for August is ready. Total: $249.00. "
            "View and pay at dashboard.stripe.com/invoices/inv_aug24. "
            "Payment due September 1st."
        ),
    },
    # ── LOW ───────────────────────────────────────────────────────────────────
    {
        "id": "L01", "exp_category": "social", "exp_priority": "low",
        "subject": "Congratulations on your promotion!",
        "body": (
            "Hey! Just heard the news — huge congrats on the VP promotion! "
            "You've really earned it. Let's catch up over coffee soon!"
        ),
    },
    {
        "id": "L02", "exp_category": "spam", "exp_priority": "low",
        "subject": "Make $5,000/week working from home — no experience needed",
        "body": (
            "Join thousands of people earning $5,000 a week from home. "
            "No experience needed. Click here to get started today. "
            "Limited spots available — act now!"
        ),
    },
    {
        "id": "L03", "exp_category": "update", "exp_priority": "low",
        "subject": "Monthly newsletter — July edition",
        "body": (
            "Welcome to the July newsletter! This month: new blog posts, product updates, "
            "upcoming webinars, and community highlights. "
            "Unsubscribe at any time via the link below."
        ),
    },
    {
        "id": "L04", "exp_category": "social", "exp_priority": "low",
        "subject": "Great meeting you at TechConf!",
        "body": (
            "Hi, it was great connecting with you at TechConf last week. "
            "I really enjoyed our conversation about distributed systems. "
            "Would love to grab coffee next time you're in town!"
        ),
    },
    {
        "id": "L05", "exp_category": "spam", "exp_priority": "low",
        "subject": "URGENT: You have won a $1,000 Amazon gift card",
        "body": (
            "Congratulations! You have been selected as our lucky winner this week. "
            "Click the link to claim your $1,000 Amazon gift card. "
            "This offer expires tonight. No purchase necessary. T&Cs apply."
        ),
    },
    {
        "id": "L06", "exp_category": "social", "exp_priority": "low",
        "subject": "Happy birthday! 🎂",
        "body": (
            "Hey! Just wanted to wish you a very happy birthday. "
            "Hope you have an amazing day. Let's celebrate soon!"
        ),
    },
    {
        "id": "L07", "exp_category": "update", "exp_priority": "low",
        "subject": "Your order #ORD-4421 has shipped",
        "body": (
            "Hi, your order has been dispatched and is expected to arrive by Friday July 18. "
            "Track your shipment using tracking number TRK-882933. "
            "No action required."
        ),
    },
    {
        "id": "L08", "exp_category": "spam", "exp_priority": "low",
        "subject": "Last chance: 90% off — sale ends TONIGHT",
        "body": (
            "FINAL HOURS! Our biggest sale ever — 90% off everything in store. "
            "Use code TONIGHT90 at checkout. Don't miss this limited-time offer! "
            "Shop now: click here."
        ),
    },
]

CATEGORY_FLEX: dict[str, set[str]] = {
    "N07": {"update", "support"},  # CVE advisory — classifiable as either
}

SEP = "-" * 68


async def run() -> int:
    passes, failures, total = 0, 0, len(EMAILS)
    print(f"\nRunning classification benchmark on {total} emails …")
    print(SEP)

    for em in EMAILS:
        result = await classify_email(em["subject"], em["body"])
        await asyncio.sleep(0.3)

        got_cat = result["category"]
        got_pri = result["priority"]
        exp_cat = em["exp_category"]
        exp_pri = em["exp_priority"]

        allowed_cats = CATEGORY_FLEX.get(em["id"], {exp_cat})
        cat_ok = got_cat in allowed_cats
        pri_ok = got_pri == exp_pri

        ok = cat_ok and pri_ok
        if ok:
            passes += 1
            status = "PASS"
        else:
            failures += 1
            status = "FAIL"

        flags = []
        if not cat_ok:
            flags.append(f"cat expected={exp_cat} got={got_cat}")
        if not pri_ok:
            flags.append(f"pri expected={exp_pri} got={got_pri}")

        flag_str = "  ✗ " + " | ".join(flags) if flags else ""
        print(
            f"  {em['id']}  {status}  [{got_cat}/{got_pri}]  "
            f"conf={result['confidence']:.2f}{flag_str}"
        )

    print(SEP)
    pct = passes / total * 100
    print(f"Result: {passes}/{total} = {pct:.0f}%  (target >= 27/30 = 90%)")
    print("BENCHMARK PASSED" if passes >= 27 else "BENCHMARK FAILED")
    return failures


if __name__ == "__main__":
    failures = asyncio.run(run())
    sys.exit(0 if failures <= 3 else 1)
