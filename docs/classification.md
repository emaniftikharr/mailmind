# Email Classification Reference

MailMind classifies every email into one **category** and one **priority level** using a LangChain LCEL chain (`llama-3.1-8b-instant` via Groq, with 3-attempt retry).

---

## Categories

| Category | Intent | Typical signals |
|---|---|---|
| **meeting** | Scheduling, calendar invites, agenda coordination | "sync", "agenda", "reschedule", calendar attachment, time slot |
| **complaint** | Dissatisfaction, disputes, refund requests, escalations | "disappointed", "damaged", "refund", "unacceptable", legal threats |
| **job** | Applications, recruiting, interviews, offer letters, HR | "application", "interview", "offer letter", "position", "onboarding" |
| **update** | Status reports, newsletters, announcements, security advisories | "sprint update", "newsletter", "CVE-", "patch", "release notes" |
| **invoice** | Billing, payment requests, receipts, purchase orders | "invoice", "due date", "payment", "overdue", "collections" |
| **support** | Help requests, bug reports, troubleshooting tickets | "how do I", "error", "broken", "not working", "please help" |
| **social** | Personal greetings, congratulations, networking | "happy birthday", "congrats", "great meeting you", "catch up" |
| **spam** | Unsolicited promotions, phishing, mass mail | "you've won", "claim now", "limited time", "earn money" |

### Disambiguation rules

**update vs support** — The key question is direction of flow:
- Someone sending you information (patch notice, security advisory, CVE announcement, status report) → **update**
- Someone asking you for help (bug report, "how do I", troubleshooting request) → **support**

**job vs meeting** — A job interview has a calendar event, but the primary intent is recruiting:
- Interview invite, offer letter, application status → **job**
- Internal team sync or recurring standup → **meeting**

**complaint vs support** — Both involve problems, but:
- Customer expressing dissatisfaction, demanding refund, or threatening escalation → **complaint**
- User reporting a technical issue or requesting guidance → **support**

---

## Priority Levels

| Level | Definition | When to use |
|---|---|---|
| **urgent** | Same-day irreversible consequence | Lawsuit filed today, full system outage for ALL users, EOD confirmation or slot is forfeited, patch due tonight, collections referral in hours |
| **high** | 24-48 hour window; serious consequence if missed | Refund demanded within 24h, offer letter expiring in 48h, partial outage actively costing money, interview tomorrow |
| **normal** | Act this week; no hard deadline | Standard invoices (30-day terms), routine meeting requests, job application acknowledgements, sprint updates |
| **low** | No action required | Newsletters, social greetings, spam — always low regardless of claimed urgency |

### Priority decision guide

Apply these rules top-to-bottom; the first match wins:

```
Is there an action required TODAY (by end of day)?
  Yes → Is the consequence same-day and irreversible (legal filing, full outage, forfeited slot)?
         Yes → URGENT
         No  → HIGH  (24h window is still high, not urgent)
  No  → Is there a 1-2 day deadline with a serious consequence?
         Yes → HIGH
         No  → Is this a newsletter, social message, or spam?
                Yes → LOW
                No  → NORMAL
```

### Edge cases

| Scenario | Category | Priority | Reasoning |
|---|---|---|---|
| Customer demands refund "within 24 hours" | complaint | high | 24h window is serious but not same-day irreversible |
| Lawsuit filed today unless response in 2 hours | complaint | urgent | Same-day legal filing is irreversible |
| Interview invite for next week | job | normal | No immediate deadline |
| Interview slot forfeited unless confirmed by EOD | job | urgent | EOD confirmation with same-day forfeiture = urgent |
| Offer letter expiring in 48 hours | job | high | 48h window, not today |
| CVE/zero-day patch due midnight tonight | update | urgent | Security advisory (not support) with same-day deadline |
| Checkout broken, losing sales | support | high | Partial outage costing money; not total system failure |
| Full production database down | support | urgent | Total outage with active revenue loss |
| Newsletter with "URGENT" in subject | update | low | Claimed urgency in newsletters is always low |
| Phishing "act now or lose access" | spam | low | Spam is always low |

---

## Benchmark results

Tested on 20 ground-truth emails (2-3 per category, all 4 priority levels represented).

| Metric | Score |
|---|---|
| Category accuracy | 20/20 = 100% |
| Priority accuracy | 20/20 = 100% |
| Both correct | 20/20 = 100% |

**Model**: `llama-3.1-8b-instant` via Groq (configurable via `GROQ_MODEL` env var)  
**Chain**: `ChatPromptTemplate | ChatOpenAI | JsonOutputParser` with 3-attempt retry  
**Token budget**: ~900 tokens/call; `llama-3.1-8b-instant` has 500k TPD on Groq free tier

---

## API

```http
POST /api/v1/classify
Content-Type: application/json

{
  "subject": "FINAL NOTICE: Invoice overdue",
  "body": "Invoice #1234 is 45 days overdue. Pay within 48 hours."
}
```

Response:
```json
{
  "category": "invoice",
  "priority": "urgent",
  "confidence": 0.99,
  "reason": "Collections referral within 48 hours — imminent legal/financial consequence.",
  "all_categories": ["meeting", "complaint", "job", "update", "invoice", "support", "social", "spam"],
  "all_priorities": ["urgent", "high", "normal", "low"]
}
```
