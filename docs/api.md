# MailMind Phase 1 API Reference

Base URL: `http://localhost:8000`  
All `/api/v1/*` endpoints accept and return `application/json`.

---

## GET /health

Liveness check. No authentication required.

**Response 200**
```json
{
  "status": "ok",
  "uptime_seconds": 42.17
}
```

---

## POST /api/v1/analyze

Full email analysis: summary, action items, sentiment, tone, grammar flags, and quick replies.

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
  "email_id":      "string — echoed from request",
  "summary":       "string — 2–3 sentence overview",
  "action_items":  ["string", "..."],
  "quick_replies": ["string", "string", "string"],
  "sentiment":     "positive | neutral | negative",
  "tone":          "formal | informal | urgent | friendly",
  "grammar_issues": ["string", "..."]
}
```

**Constraints**
- `action_items`, `quick_replies`, `grammar_issues` are always arrays (never `null`).
- `sentiment` and `tone` are always one of the listed enum values; the router normalises any
  unexpected LLM output to `"neutral"` / `"formal"` respectively.
- `email_id` is opaque — the backend echoes it unchanged so the frontend can correlate
  concurrent requests.

**Errors**
| Code | Cause |
|------|-------|
| 422  | Missing required field |
| 502  | LLM provider unreachable or returned unparseable JSON |

---

## POST /api/v1/grammar

Grammar, spelling, and punctuation correction with per-correction explanations.

**Request**
```json
{
  "text": "string (required, min 1 char)"
}
```

**Response 200**
```json
{
  "corrected_text": "string — full rewritten version of input",
  "corrections": [
    {
      "original":    "string — exact phrase from input",
      "corrected":   "string — replacement phrase",
      "explanation": "string — one-sentence rationale"
    }
  ]
}
```

**Constraints**
- Empty `text` returns **422** before hitting the LLM.
- Input is silently truncated to 4 000 characters to prevent context-window overflow.
- `corrections` is always an array (never `null`).

**Errors**
| Code | Cause |
|------|-------|
| 422  | `text` is empty or missing |
| 502  | LLM provider error |

---

## POST /api/v1/rewrite-tone

Rewrites the provided text in one of six professional tones.

**Request**
```json
{
  "text": "string (required, min 1 char)",
  "tone": "formal | friendly | concise | persuasive | executive | professional"
}
```

**Response 200**
```json
{
  "rewritten":       "string — full rewritten text",
  "tone":            "string — echoed from request",
  "changes_summary": "string — brief description of what changed",
  "truncated":       false
}
```

**Constraints**
- Empty `text` returns **422**.
- `tone` must be one of the six listed values; anything else returns **422**.
- `truncated: true` means the input exceeded 2 000 characters and was clipped before being
  sent to the LLM. The rewrite covers only the first ~2 000 characters.

**Errors**
| Code | Cause |
|------|-------|
| 422  | `text` is empty, missing, or `tone` is not a supported value |
| 502  | LLM provider error |

---

## POST /api/v1/translate

Translates text into one of five supported languages.

**Request**
```json
{
  "text":            "string (required, min 1 char)",
  "target_language": "Spanish | French | German | Portuguese | Japanese"
}
```

**Response 200**
```json
{
  "translated_text":  "string",
  "source_language":  "string — detected source language",
  "target_language":  "string — echoed from request"
}
```

**Constraints**
- Empty `text` returns **422**.
- `target_language` must be exactly one of the five supported values (case-sensitive); any
  other value returns **422**.

**Errors**
| Code | Cause |
|------|-------|
| 422  | `text` is empty, missing, or `target_language` is unsupported |
| 502  | LLM provider error |

---

## POST /api/v1/summarize

Condenses long emails into 3–5 bullet points. Returns immediately without calling the LLM
if the email is under the word-count threshold.

**Request**
```json
{
  "text": "string (required)"
}
```

**Response 200**
```json
{
  "bullets":        ["string", "..."],
  "word_count":     312,
  "was_summarized": true
}
```

**Constraints**
- Emails under **300 words** return `was_summarized: false` and `bullets: []` with no LLM call.
- Emails at or above 300 words return `was_summarized: true` and 3–5 bullets.
- Input is silently truncated to 4 000 characters before the LLM call.
- Bullets never contain leading `•`, `-`, `–`, or `—` characters (stripped server-side).
- Unlike other endpoints, empty `text` is **not** rejected with 422 — it is treated as a
  zero-word email and returns `was_summarized: false`.

**Errors**
| Code | Cause |
|------|-------|
| 502  | LLM provider error |

---

## CORS Policy

The API accepts requests from:

| Origin | Purpose |
|--------|---------|
| `https://mail.google.com` | Content script injected into Gmail |
| `chrome-extension://<ID>` | Extension popup / background worker (set `CHROME_EXTENSION_ID` in `.env`) |
| `http://localhost:5173` | Vite dev server |
| `http://localhost:8000` | Local API calls during development |

Allowed methods: `GET`, `POST`. Allowed headers: `Content-Type`, `Authorization`.

---

## LLM Back-end

All AI endpoints use **Groq** via the OpenAI-compatible client:

- Base URL: `https://api.groq.com/openai/v1`
- Model: `llama-3.3-70b-versatile`
- All responses use `response_format: {"type": "json_object"}` — the LLM is always forced
  into structured JSON mode.
- Set `GROQ_API_KEY` in `backend/.env`. The key is never logged or returned to clients.
