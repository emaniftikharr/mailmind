# MailMind API Reference — Phase 1 + Phase 2

Base URL: `http://localhost:8000`  
All `/api/v1/*` endpoints accept and return `application/json`.  
CORS is enabled for `https://mail.google.com` and `http://localhost:5173`.

---

## GET /health

Liveness check. No authentication required.

**Response 200**
```json
{ "status": "ok", "uptime_seconds": 42.17 }
```

---

## POST /api/v1/pipeline  *(Phase 2 — preferred)*

Run all Phase 2 agents in a single optimised call.  
Internally executes classification + phishing + trust + links in **Wave 1** (parallel),  
then actions + replies in **Wave 2** (parallel, using classification output).

**Request**
```json
{
  "subject":  "string (optional, default '')",
  "body":     "string (required, min 1 char)",
  "sender":   "string (optional, default '')",
  "is_html":  "boolean (optional, default false)"
}
```

**Response 200**
```json
{
  "classification": { /* ClassifyResponse — see /api/v1/classify */ },
  "phishing":       { /* PhishingResponse — see /api/v1/phishing */ },
  "trust":          { /* TrustResponse — see /api/v1/trust */ },
  "links":          { /* LinkAnalysisResponse — see /api/v1/links */ },
  "actions":        { /* ActionResponse — see /api/v1/actions */ },
  "replies":        { /* ReplyResponse — see /api/v1/replies */ },
  "elapsed_ms":     1843
}
```

| Section | When to use instead of pipeline |
|---|---|
| `/api/v1/classify` | Standalone classification only |
| `/api/v1/phishing` | Standalone phishing check only |
| `/api/v1/trust` | Pre-computed link flags available |
| `/api/v1/actions` | Only action extraction needed |
| `/api/v1/replies` | Only smart replies needed |

---

## POST /api/v1/classify

Classify an email into one category and one priority level.

**Request**
```json
{ "subject": "string (optional)", "body": "string (required)" }
```

**Response 200**
```json
{
  "category":       "meeting",
  "priority":       "urgent",
  "confidence":     0.98,
  "reason":         "One-sentence explanation of the classification decision.",
  "all_categories": ["meeting","complaint","job","update","invoice","support","social","spam"],
  "all_priorities": ["urgent","high","normal","low"]
}
```

**Categories**

| Value | Meaning |
|---|---|
| `meeting` | Scheduling, invites, calendar events, agenda coordination |
| `complaint` | Dissatisfaction, disputes, refund requests, escalations |
| `job` | Job applications, recruiting, interview invites, HR onboarding |
| `update` | Status reports, newsletters, security advisories, announcements |
| `invoice` | Billing, payment requests, receipts, purchase orders |
| `support` | Help requests, bug reports, troubleshooting, service tickets |
| `social` | Personal greetings, congratulations, networking |
| `spam` | Unsolicited promotions, phishing attempts, mass mail |

**Priority levels**

| Value | When to assign |
|---|---|
| `urgent` | Same-day irreversible consequence (lawsuit filed today, full outage, EOD forfeiture) |
| `high` | 24–48 hour window, serious but not same-day |
| `normal` | Act this week — standard correspondence |
| `low` | No action needed; `spam` and `social` are always `low` |

> **Accuracy:** 27/30 = 90% on the 30-email final benchmark (July 2025).

---

## POST /api/v1/phishing

Detect phishing and social-engineering attempts.

**Request**
```json
{
  "subject": "string (optional)",
  "body":    "string (required)",
  "sender":  "string (optional) — full From header, e.g. 'PayPal <support@paypa1-secure.com>'"
}
```

**Response 200**
```json
{
  "verdict":     "phishing",
  "risk_score":  0.97,
  "indicators":  ["urgency_pressure", "lookalike_domain", "credential_request"],
  "explanation": "Fake PayPal email from a typosquatted domain demanding credential verification.",
  "safe_to_open": false
}
```

**Verdict rules**

| Verdict | Condition |
|---|---|
| `phishing` | ≥ 2 indicators present, or 1 unmistakably clear indicator |
| `suspicious` | 1–2 weaker signals, or ambiguous domain |
| `legitimate` | 0–1 minor signals with clear business context |

`safe_to_open = false` when verdict is `phishing`, or `suspicious` AND `risk_score ≥ 0.5`.

**Indicator taxonomy**

| Key | Description |
|---|---|
| `urgency_pressure` | Artificial deadline or account-threat language |
| `sender_mismatch` | Display name doesn't match sending domain |
| `lookalike_domain` | Typosquat, homoglyph, or subdomain trick (paypa1.com) |
| `suspicious_links` | Anchor ≠ href, shortener, raw IP address |
| `credential_request` | Asks for password, OTP, card, SSN, or bank details |
| `prize_scam` | Claims winner of lottery, gift card, or reward |
| `impersonation` | Mimics a known brand or institution |
| `generic_greeting` | "Dear Customer / User" instead of recipient name |
| `grammar_errors` | Unusual spelling, awkward phrasing |
| `attachment_bait` | Unexpected attachment or macro-enable instruction |

> **Accuracy:** 0 false positives on 18-email legitimate-email check (July 2025).

---

## POST /api/v1/trust

Rule-based (no LLM) trust scoring: urgency manipulation, credential harvesting, link risk.  
Synchronous — typically responds in < 10 ms.

**Request**
```json
{
  "subject":    "string (optional)",
  "body":       "string (required)",
  "is_html":    "boolean (optional, default false)",
  "link_flags": ["array of pre-computed risk flags (optional — omit to auto-extract)"]
}
```

**Response 200**
```json
{
  "trust_score":           82,
  "risk_level":            "low",
  "urgency_hits":          [{ "category": "account_threat", "matched_text": "your account will be suspended" }],
  "urgency_categories":    ["account_threat"],
  "credential_hits":       [],
  "credential_categories": [],
  "link_flags":            ["shortened_url"],
  "score_breakdown":       { "base": 100, "urgency": -5, "credentials": 0, "links": -13 },
  "summary":               "Low-risk email with one minor urgency signal."
}
```

| `risk_level` | `trust_score` range |
|---|---|
| `low` | 70–100 |
| `moderate` | 40–69 |
| `high` | 20–39 |
| `critical` | 0–19 |

---

## POST /api/v1/links

Extract and risk-score all URLs from an email body.  
Rule-based, no LLM. Synchronous.

**Request**
```json
{
  "subject": "string (optional)",
  "body":    "string (required)",
  "is_html": "boolean (optional, default false)"
}
```

**Response 200**
```json
{
  "links": [
    {
      "url":            "https://bit.ly/abc123",
      "display_text":   "Click here to verify",
      "domain":         "bit.ly",
      "display_domain": "bit.ly",
      "is_shortened":   true,
      "risk_flags":     ["shortened_url"]
    }
  ],
  "total":      3,
  "flagged":    1,
  "risk_flags": ["shortened_url"]
}
```

**Risk flags**

| Flag | Meaning |
|---|---|
| `shortened_url` | Domain is a known URL shortener |
| `domain_mismatch` | Anchor text URL domain differs from href domain |
| `brand_mismatch` | Anchor mentions a brand but href points elsewhere |
| `raw_ip_address` | href uses a numeric IP instead of a hostname |
| `redirect_param` | href contains `?url=` or similar open-redirect parameter |

---

## POST /api/v1/actions

Extract meetings, deadlines, and tasks from an email.

**Request**
```json
{
  "subject": "string (optional)",
  "body":    "string (required)",
  "sender":  "string (optional)"
}
```

**Response 200**
```json
{
  "meeting": {
    "meeting_detected":  true,
    "title":             "Q3 Strategy Session",
    "date_str":          "Thursday July 17",
    "time_str":          "2 PM",
    "duration_minutes":  60,
    "location":          "Conference Room B",
    "organizer":         "Sarah Chen",
    "attendees":         ["sarah@company.com", "alice@company.com"],
    "agenda":            "Roadmap, headcount, OKRs",
    "is_tentative":      false,
    "extraction_error":  null
  },
  "deadlines": [
    {
      "phrase":         "confirm by Wednesday",
      "resolved_date":  "2025-07-16",
      "confidence":     "high",
      "is_relative":    false,
      "urgency":        "this_week"
    }
  ],
  "tasks": [
    {
      "title":        "Confirm attendance for Q3 Strategy Session",
      "description":  "Reply to confirm by Wednesday",
      "assignee":     "me",
      "due_date_str": "Wednesday",
      "priority":     "normal"
    }
  ],
  "has_meeting":   true,
  "has_deadlines": true,
  "has_tasks":     true
}
```

**Deadline `urgency` values:** `today` · `tomorrow` · `this_week` · `next_week` · `this_month` · `future` · `asap` · `overdue`

**Task `assignee` values:** `me` (recipient) · `them` (sender/third party) · `other`

**Task `priority` values:** `urgent` · `high` · `normal` · `low`

> **Accuracy:** 20/20 = 100% on 20-email action benchmark (July 2025).

---

## POST /api/v1/replies

Generate 2–3 smart reply variants for an email.

**Request**
```json
{
  "subject":  "string (optional)",
  "body":     "string (required)",
  "sender":   "string (optional)",
  "category": "string (optional) — from /classify, improves variant intent selection",
  "priority": "string (optional, default 'normal')"
}
```

**Response 200**
```json
{
  "variants": [
    {
      "label": "Accept",
      "tone":  "formal",
      "text":  "Hi Sarah,\n\nThank you for the invitation. I'll be attending on Thursday at 2 PM.\n\n[Your Name]"
    },
    {
      "label": "Decline",
      "tone":  "formal",
      "text":  "Hi Sarah,\n\nUnfortunately I have a conflict. Could someone share the notes?\n\n[Your Name]"
    },
    {
      "label": "Propose new time",
      "tone":  "friendly",
      "text":  "Hi Sarah,\n\nThursday at 2 doesn't work for me — could we push to 4 PM?\n\nBest,\n[Your Name]"
    }
  ],
  "count":        3,
  "reply_needed": true
}
```

`reply_needed = false` for automated notifications, shipping confirmations, newsletters, and receipts — `variants` will be `[]`.

**Tone values:** `formal` · `friendly` · `direct`

> **Accuracy:** 15/15 = 100% on 15-email reply benchmark; 8/8 quality checks PASS (July 2025).

---

## POST /api/v1/summarize

Generate 3–5 bullet points for emails ≥ 300 words. Returns empty `bullets` for shorter emails.

**Request**
```json
{ "text": "string (required)" }
```

**Response 200**
```json
{
  "bullets":        ["The Q3 budget has been approved at $2.4M.", "..."],
  "word_count":     412,
  "was_summarized": true
}
```

---

## POST /api/v1/grammar

Grammar, spelling, and punctuation checking with per-correction explanations.

**Request**
```json
{ "text": "string (required)" }
```

**Response 200**
```json
{
  "corrected_text": "The meeting is scheduled for Thursday.",
  "corrections": [
    {
      "original":    "schedled",
      "corrected":   "scheduled",
      "explanation": "Spelling error: missing 'u'."
    }
  ]
}
```

---

## POST /api/v1/rewrite-tone

Rewrite an email in one of six tone styles.

**Request**
```json
{ "text": "string (required)", "tone": "formal" }
```

**Tone options:** `formal` · `friendly` · `concise` · `persuasive` · `executive` · `professional`

**Response 200**
```json
{
  "rewritten":       "Dear Team,\n\nI am writing to confirm...",
  "tone":            "formal",
  "changes_summary": "Removed contractions, added formal salutation, restructured for clarity.",
  "truncated":       false
}
```

`truncated = true` when input exceeded 2,000 characters and was clipped before rewriting.

---

## POST /api/v1/translate

Translate an email into one of five business languages.

**Request**
```json
{ "text": "string (required)", "target_language": "Spanish" }
```

**Supported languages:** `Spanish` · `French` · `German` · `Portuguese` · `Japanese`

**Response 200**
```json
{
  "translated_text":  "Estimado equipo,\n\nEscribo para confirmar...",
  "source_language":  "English",
  "target_language":  "Spanish"
}
```

---

## POST /api/v1/analyze  *(Phase 1 legacy)*

Catch-all analysis: summary, action items, sentiment, tone, grammar flags, quick replies.  
Superseded by the individual Phase 2 endpoints; retained for backwards compatibility.

**Request**
```json
{
  "email_id": "string (required)",
  "subject":  "string (required)",
  "body":     "string (required)",
  "sender":   "string (optional)"
}
```

**Response 200**
```json
{
  "email_id":      "abc123",
  "summary":       "2–3 sentence overview.",
  "action_items":  ["Reply by Wednesday", "Attach the Q3 deck"],
  "quick_replies": ["Confirmed, see you Thursday.", "Can we push to Friday?", "Happy to help — will follow up."],
  "sentiment":     "neutral",
  "tone":          "formal",
  "grammar_issues":[]
}
```

---

## Error responses

All endpoints return standard HTTP error codes:

| Code | Meaning |
|---|---|
| `400` | Validation error (missing required field, wrong type) |
| `422` | Business-logic error (unsupported language, invalid tone) |
| `502` | LLM upstream failure after all retries exhausted |
