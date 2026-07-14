"""
LCEL chain: ChatPromptTemplate | ChatOpenAI(Groq) | JsonOutputParser
Retry:      up to 3 attempts, exponential backoff with jitter
"""
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.runnables import Runnable

from app.chains.base import get_groq_llm

# ── Category definitions ──────────────────────────────────────────────────────

CATEGORIES: dict[str, str] = {
    "meeting":    "Scheduling, invites, calendar events, or agenda coordination",
    "complaint":  "Dissatisfaction, disputes, refund requests, or escalations",
    "job":        "Job applications, recruiting, interview invites, or HR onboarding",
    "update":     "Status reports, project progress, newsletters, security advisories, or announcements",
    "invoice":    "Billing, payment requests, receipts, or purchase orders",
    "support":    "Help requests, bug reports, troubleshooting, or customer service tickets",
    "social":     "Personal greetings, congratulations, networking, or event invitations",
    "spam":       "Unsolicited promotions, phishing attempts, or irrelevant mass mail",
}

CATEGORY_NAMES = list(CATEGORIES.keys())

# ── Priority definitions ──────────────────────────────────────────────────────

PRIORITIES: dict[str, str] = {
    "urgent": "Act TODAY - same-day irreversible consequence",
    "high":   "Act within 1-2 days - time-sensitive but not same-day",
    "normal": "Act this week - standard business correspondence",
    "low":    "No action required or can wait indefinitely",
}

PRIORITY_NAMES = list(PRIORITIES.keys())

MAX_INPUT_CHARS = 3_000

# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM = (
    "You are an expert email classifier. Given an email, return a single JSON object.\n\n"
    "CATEGORIES (pick exactly one):\n"
    + "\n".join(f"  {name}: {desc}" for name, desc in CATEGORIES.items())
    + "\n\nPRIORITY LEVELS (pick exactly one):\n"
    + "\n".join(f"  {name}: {desc}" for name, desc in PRIORITIES.items())
    + "\n\nPriority decision rules (apply in order):\n"
    "1. URGENT: action required by EOD today or same-day irreversible consequence — lawsuit filed today,\n"
    "   full system down for ALL users, security breach active, patch due tonight, EOD confirmation\n"
    "   required or slot/offer is forfeited, collections action within hours.\n"
    "2. HIGH: 24-48 hour window; consequence is serious but deadline is tomorrow or day after —\n"
    "   refund demanded within 24h, offer letter expiring in 48h, partial outage costing money.\n"
    "3. NORMAL: act this week; standard correspondence with no hard deadline.\n"
    "4. LOW: no action needed. Spam and social are ALWAYS low regardless of claimed urgency.\n\n"
    "Category disambiguation:\n"
    "- Security advisories, CVE announcements, and patch notifications are 'update' (they inform).\n"
    "  Only use 'support' when someone is REQUESTING help, reporting a bug, or asking to troubleshoot.\n"
    "- Job application acknowledgements, interview invites, and offer letters are always 'job'.\n\n"
    "Few-shot examples:\n\n"
    "Subject: 'Team sync Thursday 2pm'\n"
    "Body: 'Hi, let us meet Thursday at 2pm to go over sprint goals.'\n"
    '{\"category\":\"meeting\",\"priority\":\"normal\",\"confidence\":0.97,\"reason\":\"Routine calendar request; no urgency.\"}\n\n'
    "Subject: 'Extremely disappointed - demand refund within 24 hours'\n"
    "Body: 'My order arrived damaged. I have been a customer 3 years. I expect a full refund within 24 hours.'\n"
    '{\"category\":\"complaint\",\"priority\":\"high\",\"confidence\":0.96,\"reason\":\"Refund demanded within 24h is high; not a same-day irreversible consequence.\"}\n\n'
    "Subject: 'I am filing a lawsuit this afternoon'\n"
    "Body: 'My attorney will file today at 3pm unless I receive a refund within 2 hours.'\n"
    '{\"category\":\"complaint\",\"priority\":\"urgent\",\"confidence\":0.99,\"reason\":\"Legal action filed today - same-day irreversible consequence.\"}\n\n'
    "Subject: 'Interview tomorrow at 9am - confirm by EOD today'\n"
    "Body: 'Please confirm your attendance by end of today or we will offer the slot to another candidate.'\n"
    '{\"category\":\"job\",\"priority\":\"urgent\",\"confidence\":0.98,\"reason\":\"Confirmation required by EOD today or slot is forfeited - urgent.\"}\n\n'
    "Subject: 'Offer letter attached - expires in 48 hours'\n"
    "Body: 'Please review and sign the attached offer for Staff Engineer. The offer expires in 48 hours.'\n"
    '{\"category\":\"job\",\"priority\":\"high\",\"confidence\":0.95,\"reason\":\"48-hour offer window is high; deadline is not today.\"}\n\n'
    "Subject: 'Monthly newsletter - July'\n"
    "Body: 'Welcome to the July edition. New blog posts, product updates, and community events.'\n"
    '{\"category\":\"update\",\"priority\":\"low\",\"confidence\":0.97,\"reason\":\"Periodic newsletter; no action required.\"}\n\n'
    "Subject: 'CRITICAL security patch CVE-2024-1234 - apply before midnight'\n"
    "Body: 'A zero-day in OpenSSL has been disclosed. All production servers must be patched before midnight.'\n"
    '{\"category\":\"update\",\"priority\":\"urgent\",\"confidence\":0.99,\"reason\":\"Security advisory with same-day patch deadline; classified as update, not support.\"}\n\n'
    "Subject: 'Invoice #INV-0892 due in 30 days'\n"
    "Body: 'Please find attached invoice for $3,400 for web development services. Payment due August 1st.'\n"
    '{\"category\":\"invoice\",\"priority\":\"normal\",\"confidence\":0.98,\"reason\":\"Standard invoice with a 30-day window.\"}\n\n'
    "Subject: 'FINAL NOTICE: Invoice 45 days overdue - collections in 48h'\n"
    "Body: 'Invoice ($6,200) is 45 days overdue. Pay within 48 hours or your account goes to collections.'\n"
    '{\"category\":\"invoice\",\"priority\":\"urgent\",\"confidence\":0.99,\"reason\":\"Collections referral within 48 hours - imminent legal/financial consequence.\"}\n\n'
    "Subject: 'Payment checkout broken - users cannot purchase'\n"
    "Body: 'Since the 14:00 deployment the checkout page throws 500 errors. We are losing sales.'\n"
    '{\"category\":\"support\",\"priority\":\"high\",\"confidence\":0.97,\"reason\":\"Partial outage costing money but not total system failure - high, not urgent.\"}\n\n'
    "Subject: 'CRITICAL: Production DB unreachable - all users affected'\n"
    "Body: 'Our PostgreSQL cluster is down since 08:30 UTC. All logins failing. Revenue: $15k/min.'\n"
    '{\"category\":\"support\",\"priority\":\"urgent\",\"confidence\":0.99,\"reason\":\"Full outage with active revenue loss - urgent.\"}\n\n'
    "Subject: 'Great meeting you at the conference!'\n"
    "Body: 'It was great connecting at TechConf. Let us grab coffee next month.'\n"
    '{\"category\":\"social\",\"priority\":\"low\",\"confidence\":0.96,\"reason\":\"Personal networking message; no action needed.\"}\n\n'
    "Subject: 'Make $5000/week working from home'\n"
    "Body: 'Join thousands earning $5,000 a week. No experience needed. Click here now!'\n"
    '{\"category\":\"spam\",\"priority\":\"low\",\"confidence\":0.99,\"reason\":\"Unsolicited promotional message - always low.\"}\n\n'
    'Return ONLY {\"category\":\"...\",\"priority\":\"...\",\"confidence\":0.0,\"reason\":\"...\"}. No extra text.'
)

# ── Chain factory ─────────────────────────────────────────────────────────────

# SystemMessage is passed as a static object so LangChain does NOT template-parse
# the JSON few-shot examples inside it (which contain literal {braces}).
_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=_SYSTEM),
    HumanMessagePromptTemplate.from_template("{email_text}"),
])

_parser = JsonOutputParser()

_chain: Runnable | None = None


def get_classification_chain() -> Runnable:
    """
    Lazy singleton: builds prompt | LLM | parser and wraps it with
    up to 3 retry attempts (exponential backoff + jitter).
    """
    global _chain
    if _chain is None:
        llm = get_groq_llm(max_tokens=150)
        _chain = (_prompt | llm | _parser).with_retry(
            retry_if_exception_type=(Exception,),
            stop_after_attempt=3,
            wait_exponential_jitter=True,
        )
    return _chain
