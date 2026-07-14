"""
Phishing detection false-positive check — backend/tests/test_phishing_fp.py

Tests 18 LEGITIMATE business emails.  Every one should come back as
"legitimate" or "suspicious" (with risk_score < 0.5 and safe_to_open=True).
A "phishing" verdict on a legitimate email is a false positive (FP).

Pass threshold: 0 false positives (verdict="phishing" on a legitimate email).
Warning zone:  "suspicious" with risk_score >= 0.5 is flagged as a near-miss.

Categories covered
------------------
  Corporate internal   INT01-INT04
  Vendor / SaaS        VEN01-VEN04
  HR / job             HR01-HR03
  Finance / billing    FIN01-FIN03
  Developer tooling    DEV01-DEV02
  Marketing            MKT01-MKT02

Run: python backend/tests/test_phishing_fp.py
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

from app.phishing_agent import detect_phishing

EMAILS = [
    # ── Corporate internal ─────────────────────────────────────────────────────
    {
        "id": "INT01",
        "subject": "Q3 planning sync — Thursday 2 PM in Room 4B",
        "body": "Hi team, I've booked a Q3 planning session for Thursday at 2 PM in Room 4B. Agenda: roadmap, headcount, and OKRs. Calendar invite coming shortly. — Sarah",
        "sender": "sarah.chen@acmecorp.com",
    },
    {
        "id": "INT02",
        "subject": "Reminder: all-hands Friday at 10 AM",
        "body": "Just a reminder that the all-hands is this Friday at 10 AM in the main auditorium. Lunch will be provided. Please RSVP in the Slack channel so we can order enough. See you there! — People Ops",
        "sender": "peopleops@acmecorp.com",
    },
    {
        "id": "INT03",
        "subject": "Your expense report ER-2024-0831 has been approved",
        "body": "Hi James, your expense report ER-2024-0831 ($342.50) has been approved by your manager and submitted to payroll. Reimbursement will appear in your next pay cycle. Questions? Reply to this email.",
        "sender": "expenses@acmecorp.com",
    },
    {
        "id": "INT04",
        "subject": "IT: VPN client update required by end of week",
        "body": "Hi, the IT team is rolling out VPN client v4.2 this week to address compatibility with macOS Sequoia. Please update your Cisco AnyConnect client via Software Center before Friday. No credentials required — the update is automatic. IT Help Desk",
        "sender": "helpdesk@acmecorp.com",
    },
    # ── Vendor / SaaS ──────────────────────────────────────────────────────────
    {
        "id": "VEN01",
        "subject": "Your GitHub Actions minutes usage — July 2024",
        "body": "Hi Jane, you used 3,240 of your 3,000 included minutes this month. Your overage charge of $1.28 will be billed to your payment method on file. View full usage breakdown at github.com/settings/billing. The GitHub Team",
        "sender": "noreply@github.com",
    },
    {
        "id": "VEN02",
        "subject": "Stripe invoice INV-2024-09871 for $249.00",
        "body": "Hi Jane, your Stripe invoice for $249.00 is ready. View and pay at https://dashboard.stripe.com/invoices/inv_2024_09871. Payment due August 15th. If you have questions, visit stripe.com/support. Thank you for using Stripe.",
        "sender": "billing@stripe.com",
    },
    {
        "id": "VEN03",
        "subject": "AWS Monthly Statement — July 2024",
        "body": "Your AWS account (Account ID: 123456789012) statement for July 2024 is now available. Total charges: $1,847.32. View your detailed bill at https://console.aws.amazon.com/billing/. Amazon Web Services",
        "sender": "aws-billing@amazon.com",
    },
    {
        "id": "VEN04",
        "subject": "Your Slack workspace upgraded to Business+ — receipt enclosed",
        "body": "Hi, thank you for upgrading Acme Corp's Slack workspace to Business+. Your receipt: $7.25 per active user × 48 users = $348.00 for the period Aug 1 – Aug 31. Manage your subscription at app.slack.com/manage. The Slack Team",
        "sender": "feedback@slack.com",
    },
    # ── HR / Job ───────────────────────────────────────────────────────────────
    {
        "id": "HR01",
        "subject": "Application received — Senior Engineer at TechCo",
        "body": "Hi Alex, thank you for applying for the Senior Engineer position at TechCo. We have received your application and will review it over the next 5–7 business days. If you are selected for a phone screen, you will hear from our team shortly. Best, TechCo Talent Team",
        "sender": "talent@techco.io",
    },
    {
        "id": "HR02",
        "subject": "Offer letter attached — Staff Engineer, Base: $195k",
        "body": "Hi Alex, we are thrilled to extend an offer for the Staff Engineer role at TechCo. Please find your offer letter attached. The offer includes a base salary of $195,000, equity, and full benefits. Please review and sign at your earliest convenience. We look forward to having you join us! — Emma, Head of Talent",
        "sender": "emma.jones@techco.io",
    },
    {
        "id": "HR03",
        "subject": "Onboarding checklist: your first day is Monday",
        "body": "Hi Alex! Your first day at TechCo is this Monday. Here is your onboarding checklist: 1) Complete I-9 on Workday 2) Pick up your laptop from reception 3) Join the #onboarding Slack channel. Your manager James will meet you at 9 AM. See you Monday! — People Ops",
        "sender": "onboarding@techco.io",
    },
    # ── Finance / Billing ──────────────────────────────────────────────────────
    {
        "id": "FIN01",
        "subject": "Invoice #3382 from Webflow — $39.00/month",
        "body": "Hi, your Webflow invoice for August is attached. Amount: $39.00 for the CMS plan. This will be auto-charged to your Visa ending in 4242 on August 1st. View your billing history at webflow.com/dashboard/billing. — Webflow Billing",
        "sender": "billing@webflow.com",
    },
    {
        "id": "FIN02",
        "subject": "Payment confirmation — $2,400 received",
        "body": "Dear Acme Corp, this confirms we received payment of $2,400 for invoice #INV-2024-07. Your account balance is now $0.00. A receipt has been attached for your records. Thank you for your prompt payment. — Accounts Receivable, DesignStudio LLC",
        "sender": "ar@designstudio.com",
    },
    {
        "id": "FIN03",
        "subject": "Wire transfer confirmation — $15,000 sent to Vendor",
        "body": "Transaction Reference: WT-2024-0731-882. Amount: $15,000.00 USD. Beneficiary: Acme Suppliers Ltd. Status: Completed. Settlement date: 2024-07-31. For questions contact your relationship manager or call 1-800-BANK. First National Bank",
        "sender": "notifications@firstnationalbank.com",
    },
    # ── Developer tooling ──────────────────────────────────────────────────────
    {
        "id": "DEV01",
        "subject": "[GitHub] Pull request #441 approved by @bob",
        "body": "@alice — Bob approved your pull request 'feat: add rate limiting to API (#441)'. All required reviews have been completed. You can merge this pull request. View it at github.com/acme/backend/pull/441",
        "sender": "notifications@github.com",
    },
    {
        "id": "DEV02",
        "subject": "Vercel deployment succeeded — production",
        "body": "Your latest deployment to production succeeded. Branch: main. Commit: a3f9b21 'fix: correct redirect loop on /login'. Deployed to: acme.vercel.app. Build time: 47s. View deployment details at vercel.com/acme/dashboard. — Vercel",
        "sender": "noreply@vercel.com",
    },
    # ── Marketing (legitimate) ─────────────────────────────────────────────────
    {
        "id": "MKT01",
        "subject": "Figma Config 2024 — register before spaces fill up",
        "body": "Hi Jane, Figma Config 2024 is happening October 2nd in San Francisco. Join 5,000+ designers and developers for talks, workshops, and community time. Early bird tickets are available at config.figma.com. We hope to see you there! — The Figma Team",
        "sender": "events@figma.com",
    },
    {
        "id": "MKT02",
        "subject": "New in Notion: AI-powered search — try it now",
        "body": "Hey Jane, we just launched AI-powered search in Notion. Start a search in any workspace and watch it find exactly what you're looking for — across pages, databases, and linked docs. Learn more at notion.so/ai. — The Notion Team",
        "sender": "team@mail.notion.so",
    },
]

SEP = "-" * 68


async def run() -> int:
    false_positives = 0
    near_misses = 0
    print(f"\nPhishing false-positive check on {len(EMAILS)} LEGITIMATE emails …")
    print(SEP)

    for em in EMAILS:
        result = await detect_phishing(em["subject"], em["body"], em["sender"])
        await asyncio.sleep(0.3)

        verdict    = result["verdict"]
        risk       = result["risk_score"]
        safe       = result["safe_to_open"]
        indicators = result["indicators"]

        is_fp      = verdict == "phishing"
        is_nm      = verdict == "suspicious" and risk >= 0.5

        if is_fp:
            false_positives += 1
            status = "FP  "
        elif is_nm:
            near_misses += 1
            status = "WARN"
        else:
            status = "ok  "

        ind_str = f"  [{', '.join(indicators)}]" if indicators else ""
        print(
            f"  {em['id']}  {status}  {verdict:10s}  risk={risk:.2f}  "
            f"safe={safe}{ind_str}"
        )

    print(SEP)
    print(
        f"False positives: {false_positives}  "
        f"Near-misses (suspicious ≥0.5): {near_misses}"
    )
    print(f"(pass threshold: 0 false positives)")
    print("FP CHECK PASSED" if false_positives == 0 else "FP CHECK FAILED")
    return false_positives


if __name__ == "__main__":
    fp = asyncio.run(run())
    sys.exit(0 if fp == 0 else 1)
