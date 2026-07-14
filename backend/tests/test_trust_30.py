"""
30-email benchmark for social_engineering.analyze_trust().

Pass criteria
  Phishing (15 samples): trust_score <= 65
  Legitimate (15 samples): trust_score >= 60

Run with:  python backend/tests/test_trust_30.py
"""
import sys
sys.path.insert(0, "backend")

from app.social_engineering import analyze_trust

# ── Test corpus ───────────────────────────────────────────────────────────────

PHISHING = [
    {
        "id": "P01",
        "subject": "URGENT: Your PayPal account has been suspended",
        "body": (
            "Dear Customer, We detected suspicious activity on your PayPal account. "
            "Your account has been temporarily suspended. You must verify your information "
            "within 24 hours or your account will be permanently closed. "
            "Please enter your current password and credit card number to restore access: "
            "http://paypa1-secure.com/verify. Failure to comply will result in legal action."
        ),
        "link_flags": ["domain_mismatch", "brand_mismatch"],
    },
    {
        "id": "P02",
        "subject": "Final Notice: IRS Legal Action Pending",
        "body": (
            "This is your final warning from the IRS. A warrant has been issued for your "
            "arrest due to unpaid taxes. You must respond immediately or face prosecution. "
            "Provide your Social Security Number and bank account number for verification."
        ),
        "link_flags": ["raw_ip_address"],
    },
    {
        "id": "P03",
        "subject": "Microsoft 365: Verify your credentials now",
        "body": (
            "Your Microsoft 365 account will expire within 24 hours. "
            "Act now to prevent losing access to your emails and files. "
            "Click here and enter your password to keep your account active: "
            "http://micros0ft-verify.net/login"
        ),
        "link_flags": ["domain_mismatch", "brand_mismatch"],
    },
    {
        "id": "P04",
        "subject": "Your Bank of America account has been locked",
        "body": (
            "Suspicious activity detected on your account. Your account has been locked "
            "to protect you. You must verify your bank account number and routing number "
            "immediately or access will be permanently revoked. "
            "Do not delay — respond right away."
        ),
        "link_flags": [],
    },
    {
        "id": "P05",
        "subject": "You have an unclaimed reward of $5,000!",
        "body": (
            "Congratulations! You have a pending reward of $5,000 that expires today. "
            "This is your final notice. You must claim your prize before midnight or forfeit "
            "your funds. Provide your bank account details to receive the transfer."
        ),
        "link_flags": ["shortened_url"],
    },
    {
        "id": "P06",
        "subject": "Your computer has been hacked — act immediately",
        "body": (
            "We detected unauthorized access to your computer. Your files are at risk. "
            "You must respond immediately by calling our security hotline or your data "
            "will be deleted within 24 hours. Provide your password to allow remote recovery."
        ),
        "link_flags": [],
    },
    {
        "id": "P07",
        "subject": "Apple ID: Verify your account immediately",
        "body": (
            "Your Apple ID has been suspended due to unusual sign-in activity. "
            "Act now — your account will be closed if you do not verify within 24 hours. "
            "Enter your current password and date of birth at the link below."
        ),
        "link_flags": ["brand_mismatch"],
    },
    {
        "id": "P08",
        "subject": "Netflix: Payment failed — update your card now",
        "body": (
            "Your Netflix payment failed. Your account will be suspended today unless "
            "you update your billing information. Please provide your credit card number, "
            "CVV and expiry date immediately to avoid losing access."
        ),
        "link_flags": ["domain_mismatch"],
    },
    {
        "id": "P09",
        "subject": "Amazon: Your package is held — verify card to release",
        "body": (
            "Your package cannot be delivered due to a payment issue. "
            "You must verify your credit card details within 48 hours or the parcel "
            "will be returned. Enter your 16-digit card number to confirm delivery."
        ),
        "link_flags": ["brand_mismatch"],
    },
    {
        "id": "P10",
        "subject": "COVID-19 Refund — Final Notice",
        "body": (
            "You are eligible for a COVID-19 tax refund of $1,200. "
            "This is your final notice — the deadline is today. "
            "To process your refund, provide your Social Security Number and bank account "
            "number. Failure to respond will result in forfeiture of your funds."
        ),
        "link_flags": [],
    },
    {
        "id": "P11",
        "subject": "Congratulations — Job Offer (Advance Payment Required)",
        "body": (
            "You have been selected for a high-paying remote job. To activate your position "
            "you must pay an advance processing fee via wire transfer. "
            "Provide your bank account number and routing number to complete the enrollment. "
            "Offer expires today — act now."
        ),
        "link_flags": [],
    },
    {
        "id": "P12",
        "subject": "FBI Cybercrime Division: Immediate Action Required",
        "body": (
            "This is the FBI Cybercrime Division. A warrant has been issued in your name "
            "for illegal online activity. You must respond immediately or face arrest. "
            "To resolve this matter, verify your identity by providing your SSN and "
            "national ID number within 24 hours."
        ),
        "link_flags": [],
    },
    {
        "id": "P13",
        "subject": "Chase Bank: Suspicious Activity Detected",
        "body": (
            "We have detected suspicious activity on your Chase account. "
            "Your account has been temporarily blocked. To restore access, you must "
            "provide your account number and routing number immediately. "
            "Do not delay — your account will be closed within 48 hours."
        ),
        "link_flags": [],
    },
    {
        "id": "P14",
        "subject": "DHL: Delivery Failed — Payment Required",
        "body": (
            "Your DHL package could not be delivered due to an outstanding payment. "
            "You must pay within 24 hours or your parcel will be returned. "
            "Enter your credit card number and CVV to release your shipment: "
            "http://dhl-delivery-secure.com/pay"
        ),
        "link_flags": ["domain_mismatch", "brand_mismatch"],
    },
    {
        "id": "P15",
        "subject": "LinkedIn: Your account will be closed",
        "body": (
            "Unusual activity has been detected on your LinkedIn account. "
            "Your account will be suspended within 24 hours unless you verify your "
            "identity. Enter your current password and confirm your date of birth "
            "to restore access immediately."
        ),
        "link_flags": ["brand_mismatch"],
    },
]

LEGITIMATE = [
    {
        "id": "L01",
        "subject": "Invoice #INV-2025-0042 from Stripe",
        "body": (
            "Hi Jane, your invoice for $149.00 is ready. You can view and download it "
            "at https://dashboard.stripe.com/invoices/INV-2025-0042. "
            "Payment is due on 2025-08-01. Thank you for your business. — Stripe Billing"
        ),
        "link_flags": [],
    },
    {
        "id": "L02",
        "subject": "PR #247 reviewed: Add retry logic to classification chain",
        "body": (
            "Hey, I reviewed your PR. The retry logic looks solid. One suggestion: "
            "consider adding a max_delay cap to avoid unbounded backoff. Otherwise LGTM. "
            "https://github.com/acme/mailmind/pull/247"
        ),
        "link_flags": [],
    },
    {
        "id": "L03",
        "subject": "Team sync — Monday 10am",
        "body": (
            "Hi team, just a reminder about our weekly sync this Monday at 10am. "
            "Agenda: Q3 roadmap review, sprint planning, and any blockers. "
            "Video link will be sent 10 minutes before. See you then!"
        ),
        "link_flags": [],
    },
    {
        "id": "L04",
        "subject": "Welcome to the MailMind newsletter",
        "body": (
            "You've successfully subscribed to the MailMind newsletter. "
            "You'll receive monthly updates on new features and AI email tips. "
            "You can unsubscribe at any time by clicking the link at the bottom of any email."
        ),
        "link_flags": [],
    },
    {
        "id": "L05",
        "subject": "Your order has shipped — tracking inside",
        "body": (
            "Great news! Your order #ORD-88421 has shipped. "
            "Expected delivery: Tuesday, July 15. "
            "Track your package at https://ups.com/track?id=1Z9999W99999999999. "
            "Questions? Contact our support team."
        ),
        "link_flags": [],
    },
    {
        "id": "L06",
        "subject": "Application received — Software Engineer role",
        "body": (
            "Thank you for applying for the Software Engineer position at Acme Corp. "
            "We have received your application and will review it within 5–7 business days. "
            "You will hear from our recruiting team if your profile matches our needs."
        ),
        "link_flags": [],
    },
    {
        "id": "L07",
        "subject": "Payroll direct deposit setup — action needed",
        "body": (
            "Hi Alex, to set up your direct deposit for payroll, please provide your "
            "bank account number and routing number via our secure HR portal at "
            "https://hr.acmecorp.internal/payroll-setup. "
            "This is required before your first paycheck on August 1."
        ),
        "link_flags": [],
        "note": "Legitimately requests bank details — expect moderate score",
    },
    {
        "id": "L08",
        "subject": "MailMind v2.3 released — what's new",
        "body": (
            "MailMind v2.3 is here! This release includes improved phishing detection, "
            "faster classification, and a new trust score UI. "
            "Read the full changelog at https://mailmind.dev/changelog/v2.3. "
            "Thanks for being a user!"
        ),
        "link_flags": [],
    },
    {
        "id": "L09",
        "subject": "Re: Support ticket #4492 — resolved",
        "body": (
            "Hi Sam, I wanted to follow up on your support ticket #4492 regarding "
            "the import error you were seeing. Our team has deployed a fix in v2.2.8. "
            "Please update and let us know if the issue persists. Happy to help further."
        ),
        "link_flags": [],
    },
    {
        "id": "L10",
        "subject": "PyCon 2025 — registration confirmed",
        "body": (
            "Your registration for PyCon 2025 (May 14–18, Pittsburgh) is confirmed. "
            "Your ticket ID is PYC-2025-00847. Hotel block details and schedule will "
            "be sent in a follow-up email. See you in Pittsburgh!"
        ),
        "link_flags": [],
    },
    {
        "id": "L11",
        "subject": "July salary slip",
        "body": (
            "Hi Alex, please find attached your salary slip for July 2025. "
            "Net pay: $6,250.00. Deposited to your bank account on file on July 31. "
            "Contact HR if you have any questions."
        ),
        "link_flags": [],
    },
    {
        "id": "L12",
        "subject": "Reminder: Q3 milestone due Friday",
        "body": (
            "Hi team, just a reminder that the Q3 feature milestone is due this Friday. "
            "Please make sure your PRs are merged and tests are passing by EOD Thursday "
            "so we have buffer for QA. Let me know if you're blocked on anything."
        ),
        "link_flags": [],
    },
    {
        "id": "L13",
        "subject": "IT Security: Annual penetration test report",
        "body": (
            "Hi, please find the annual penetration test report for FY2025 attached. "
            "The security audit identified 2 low-severity findings, both already patched. "
            "No critical vulnerabilities were found. Full report available in the IT portal."
        ),
        "link_flags": [],
    },
    {
        "id": "L14",
        "subject": "Jane Smith accepted your LinkedIn connection",
        "body": (
            "Hi Alex, Jane Smith has accepted your connection request on LinkedIn. "
            "You can now message Jane and see her full profile. "
            "View Jane's profile at https://linkedin.com/in/janesmith."
        ),
        "link_flags": [],
    },
    {
        "id": "L15",
        "subject": "Your Spotify Premium subscription renews on Aug 1",
        "body": (
            "Hi Alex, your Spotify Premium subscription will automatically renew on "
            "August 1, 2025 for $9.99/month. No action needed — your payment method on "
            "file will be charged. To manage your subscription, visit "
            "https://spotify.com/account."
        ),
        "link_flags": [],
    },
]

# ── Runner ────────────────────────────────────────────────────────────────────

PHISHING_PASS_THRESHOLD   = 65   # score must be <= this
LEGITIMATE_PASS_THRESHOLD = 60   # score must be >= this

def run():
    phish_passes = 0
    legit_passes  = 0
    failures: list[str] = []

    header = f"{'ID':<5} {'Score':>5}  {'Level':<10}  {'Verdict':<6}  Subject"
    print("\n" + "=" * 72)
    print("PHISHING SAMPLES  (expect score <= 65)")
    print("=" * 72)
    print(header)
    print("-" * 72)

    for sample in PHISHING:
        r = analyze_trust(sample["subject"], sample["body"],
                          link_flags=sample.get("link_flags", []))
        passed = r.trust_score <= PHISHING_PASS_THRESHOLD
        mark = "PASS" if passed else "FAIL"
        if passed:
            phish_passes += 1
        else:
            failures.append(f"[{sample['id']}] {sample['subject'][:50]} — score {r.trust_score}")
        subj = sample["subject"][:45]
        print(f"{sample['id']:<5} {r.trust_score:>5}  {r.risk_level:<10}  {mark:<6}  {subj}")

    print()
    print("=" * 72)
    print("LEGITIMATE SAMPLES  (expect score >= 60)")
    print("=" * 72)
    print(header)
    print("-" * 72)

    for sample in LEGITIMATE:
        r = analyze_trust(sample["subject"], sample["body"],
                          link_flags=sample.get("link_flags", []))
        passed = r.trust_score >= LEGITIMATE_PASS_THRESHOLD
        mark = "PASS" if passed else "FAIL"
        if passed:
            legit_passes += 1
        else:
            failures.append(f"[{sample['id']}] {sample['subject'][:50]} — score {r.trust_score}")
        subj = sample["subject"][:45]
        note = " *" if sample.get("note") else ""
        print(f"{sample['id']:<5} {r.trust_score:>5}  {r.risk_level:<10}  {mark:<6}  {subj}{note}")

    print()
    print("=" * 72)
    total = len(PHISHING) + len(LEGITIMATE)
    passed = phish_passes + legit_passes
    pct = passed / total * 100
    print(f"RESULT: {passed}/{total} passed ({pct:.0f}%)")
    print(f"  Phishing detection:   {phish_passes}/{len(PHISHING)}")
    print(f"  False positive rate:  {len(LEGITIMATE) - legit_passes}/{len(LEGITIMATE)}")
    if failures:
        print("\nFailed samples:")
        for f in failures:
            print(f"  {f}")
    print("=" * 72 + "\n")
    return passed, total, failures

if __name__ == "__main__":
    passed, total, failures = run()
    sys.exit(0 if len(failures) == 0 else 1)
