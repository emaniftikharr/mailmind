"""
LCEL chain for phishing / social-engineering detection.

Pattern coverage (10 indicator classes):
  urgency_pressure  - Artificial deadline or fear trigger ("account suspended", "act now")
  sender_mismatch   - Display name does not match the actual sending domain
  lookalike_domain  - Domain mimics a brand via typo, homoglyph, or subdomain trick
                      (paypa1.com, amazon-secure.net, paypal.com.hacker.net)
  suspicious_links  - Anchor text differs from href; redirect chains; URL shorteners;
                      raw IP addresses (http://185.x.x.x/login)
  credential_request- Asks for password, OTP, card number, SSN, or bank details via email
  prize_scam        - Claims user won a lottery, gift card, or reward
  impersonation     - Mimics a known brand or institution (PayPal, Microsoft, IRS, bank)
  generic_greeting  - "Dear Customer" / "Dear User" instead of recipient's real name
  grammar_errors    - Unusual spelling, awkward phrasing, inconsistent formatting
  attachment_bait   - Unexpected attachment or instruction to enable macros/content

Chain: SystemMessage(static) | HumanMessagePromptTemplate | ChatOpenAI(Groq) | JsonOutputParser
Retry: up to 3 attempts, exponential backoff with jitter
"""
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.runnables import Runnable

from app.chains.base import get_groq_llm

# ── Indicator taxonomy ────────────────────────────────────────────────────────

PHISHING_INDICATORS: dict[str, str] = {
    "urgency_pressure":   "Artificial urgency or fear (account suspended, limited time, act now)",
    "sender_mismatch":    "Display name does not match the actual sending domain",
    "lookalike_domain":   "Domain mimics a brand via typo, homoglyph, or subdomain trick",
    "suspicious_links":   "Link anchor text differs from URL; redirect/shortener; raw IP address",
    "credential_request": "Asks for password, OTP, card number, SSN, or bank details via email",
    "prize_scam":         "Claims recipient won a lottery, gift card, prize, or reward",
    "impersonation":      "Mimics a known brand or institution (PayPal, Microsoft, IRS, bank)",
    "generic_greeting":   "Uses 'Dear Customer' or 'Dear User' instead of recipient's real name",
    "grammar_errors":     "Unusual spelling mistakes, awkward phrasing, or inconsistent formatting",
    "attachment_bait":    "Unexpected attachment or instructs to enable macros or content",
}

INDICATOR_NAMES = list(PHISHING_INDICATORS.keys())
VERDICTS = ("phishing", "suspicious", "legitimate")
MAX_INPUT_CHARS = 3_000

# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM = (
    "You are a cybersecurity expert specializing in email phishing detection.\n"
    "Analyze the email and return a single JSON object.\n\n"
    "PHISHING INDICATORS — report every one that is present:\n"
    + "\n".join(f"  {k}: {v}" for k, v in PHISHING_INDICATORS.items())
    + "\n\nVERDICT OPTIONS:\n"
    "  phishing:   High confidence this is a phishing or social-engineering attempt.\n"
    "  suspicious: Shows 1-2 weaker signals; treat with caution but not conclusive.\n"
    "  legitimate: Appears genuine; no significant phishing signals detected.\n\n"
    "VERDICT RULES (apply in order):\n"
    "1. phishing  — 2+ indicators present, OR 1 unmistakably clear indicator\n"
    "   (e.g. prize_scam + credential_request, lookalike_domain + suspicious_links).\n"
    "2. suspicious — 1-2 weaker signals (urgency in marketing, generic greeting in bulk mail),\n"
    "   OR ambiguous sender domain that cannot be confirmed as legitimate.\n"
    "3. legitimate — 0-1 minor signals with clear, consistent business context.\n\n"
    "safe_to_open rules:\n"
    "  false  if verdict is 'phishing'\n"
    "  false  if verdict is 'suspicious' AND risk_score >= 0.5\n"
    "  true   otherwise\n\n"
    "Few-shot examples:\n\n"
    # 1 — legitimate business email
    "From: Alice Johnson <alice@acmecorp.com>\n"
    "Subject: Q3 budget review — Thursday 3pm\n"
    "Body: Hi team, please join the Q3 budget review on Thursday at 3pm in Room B. Agenda attached.\n"
    '{\"verdict\":\"legitimate\",\"risk_score\":0.02,\"indicators\":[],\"explanation\":\"Internal scheduling email from a matching corporate domain with no phishing signals.\",\"safe_to_open\":true}\n\n'
    # 2 — PayPal credential phish (impersonation + lookalike domain + credential_request + urgency)
    "From: PayPal Support <support@paypa1-secure.com>\n"
    "Subject: Your PayPal account has been SUSPENDED - verify now\n"
    "Body: Dear Customer, We detected unusual activity on your account. "
    "Your account is suspended until you verify your identity. "
    "Click here to restore access: http://paypa1-secure.com/verify. "
    "Failure to verify within 24 hours will result in permanent closure.\n"
    '{\"verdict\":\"phishing\",\"risk_score\":0.98,\"indicators\":[\"urgency_pressure\",\"sender_mismatch\",\"lookalike_domain\",\"credential_request\",\"impersonation\",\"generic_greeting\"],\"explanation\":\"Fake PayPal email from a typosquatted domain (paypa1-secure.com) demanding credential verification under threat of account closure — classic phishing.\",\"safe_to_open\":false}\n\n'
    # 3 — Prize/lottery scam
    "From: AWS Prize Team <noreply@amazon-rewards-claim.net>\n"
    "Subject: You have been selected! Claim your $1,000 Amazon gift card\n"
    "Body: Congratulations! You are our lucky winner this week. "
    "To claim your $1,000 Amazon gift card, click the link and enter your name, address, and credit card for shipping verification. "
    "Offer expires in 1 hour!\n"
    '{\"verdict\":\"phishing\",\"risk_score\":0.99,\"indicators\":[\"urgency_pressure\",\"lookalike_domain\",\"credential_request\",\"prize_scam\",\"impersonation\"],\"explanation\":\"Lottery scam from a domain impersonating Amazon, requesting credit card details under a fabricated prize, with artificial urgency.\",\"safe_to_open\":false}\n\n'
    # 4 — Microsoft 365 credential phish
    "From: Microsoft 365 <no-reply@microsoft-365-login.net>\n"
    "Subject: Action required: Your Microsoft 365 password expires today\n"
    "Body: Dear User, your Microsoft 365 password will expire today. "
    "Please update your password immediately by clicking: https://bit.ly/m365pwd-update\n"
    '{\"verdict\":\"phishing\",\"risk_score\":0.97,\"indicators\":[\"urgency_pressure\",\"lookalike_domain\",\"suspicious_links\",\"credential_request\",\"impersonation\",\"generic_greeting\"],\"explanation\":\"Microsoft impersonation using a lookalike domain and a URL shortener to hide a credential-harvesting link, pressured by a false expiration deadline.\",\"safe_to_open\":false}\n\n'
    # 5 — IRS refund scam
    "From: IRS Refund Center <irs-refund@gov-irs-refunds.com>\n"
    "Subject: IRS: You have a pending tax refund of $847.00\n"
    "Body: Dear Taxpayer, our records show you are eligible for a tax refund of $847.00. "
    "To receive your refund, you must verify your Social Security Number and bank account details at: "
    "http://192.168.22.45/irs-refund. This offer expires in 48 hours.\n"
    '{\"verdict\":\"phishing\",\"risk_score\":0.99,\"indicators\":[\"urgency_pressure\",\"sender_mismatch\",\"lookalike_domain\",\"suspicious_links\",\"credential_request\",\"impersonation\"],\"explanation\":\"IRS impersonation requesting SSN and bank details via a raw IP address — the IRS never requests sensitive information by email.\",\"safe_to_open\":false}\n\n'
    # 6 — spear phishing (targeted, harder to spot)
    "From: John Smith - IT <john.smith@acmecorpp.com>\n"
    "Subject: Urgent: VPN certificate renewal required by EOD\n"
    "Body: Hi, our VPN certificate is expiring today. Please log in and re-authenticate at "
    "https://vpn.acmecorpp.com/renew before 5pm to avoid losing access. — IT Department\n"
    '{\"verdict\":\"phishing\",\"risk_score\":0.88,\"indicators\":[\"urgency_pressure\",\"sender_mismatch\",\"lookalike_domain\",\"suspicious_links\"],\"explanation\":\"Spear phish impersonating an internal IT department via a one-character typo domain (acmecorpp.com vs acmecorp.com) with an artificial EOD deadline.\",\"safe_to_open\":false}\n\n'
    # 7 — suspicious marketing (not phishing, but aggressive)
    "From: Deals Team <deals@flash-sale-store.com>\n"
    "Subject: LAST CHANCE - 90% OFF ends TONIGHT!\n"
    "Body: Dear Valued Customer, this is your final chance to grab our biggest sale of the year. "
    "90% off all items — tonight only! Click now before it's gone.\n"
    '{\"verdict\":\"suspicious\",\"risk_score\":0.38,\"indicators\":[\"urgency_pressure\",\"generic_greeting\"],\"explanation\":\"Aggressive promotional email with urgency and a generic greeting; no credential request or domain spoofing — suspicious marketing, not phishing.\",\"safe_to_open\":true}\n\n'
    # 8 — legitimate invoice from vendor
    "From: Billing <billing@stripe.com>\n"
    "Subject: Your Stripe invoice INV-2024-09871 for $149.00\n"
    "Body: Hi Jane, your invoice for $149.00 is ready. "
    "You can view it at https://dashboard.stripe.com/invoices/INV-2024-09871. "
    "Payment is due by August 15th. Thank you for using Stripe.\n"
    '{\"verdict\":\"legitimate\",\"risk_score\":0.05,\"indicators\":[],\"explanation\":\"Invoice email from stripe.com using the recipient\'s name, linking to the official stripe.com dashboard — no phishing signals.\",\"safe_to_open\":true}\n\n'
    'Return ONLY {\"verdict\":\"...\",\"risk_score\":0.0,\"indicators\":[\"...\"],\"explanation\":\"...\",\"safe_to_open\":true}. No extra text.'
)

# ── Chain factory ─────────────────────────────────────────────────────────────

_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=_SYSTEM),
    HumanMessagePromptTemplate.from_template("{email_text}"),
])

_parser = JsonOutputParser()

_chain: Runnable | None = None


def get_phishing_chain() -> Runnable:
    """
    Lazy singleton: builds prompt | LLM | parser with 3-attempt retry.
    Uses max_tokens=256 to accommodate the indicators list.
    """
    global _chain
    if _chain is None:
        llm = get_groq_llm(max_tokens=256)
        _chain = (_prompt | llm | _parser).with_retry(
            retry_if_exception_type=(Exception,),
            stop_after_attempt=3,
            wait_exponential_jitter=True,
        )
    return _chain
