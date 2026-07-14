# MailMind — Teammate Handoff (Phase 2)

This document gives a new contributor enough context to run the project, understand
the key design decisions, and pick up Phase 3 work without reading every file.

---

## What MailMind is

A Chrome MV3 extension that injects a sidebar into Gmail and surfaces AI-powered
insights about the open email. No email content reaches third-party servers except
Groq (which you control via your own API key).

**Current state:** Phase 2 complete. The sidebar shows classification, phishing
risk, action extraction (meetings / deadlines / tasks), and smart replies — all
from a single `/api/v1/pipeline` call.

---

## Quick start

```bash
# 1. Clone and install
git clone <repo>
cd mailmind

# 2. Backend
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows
cp .env.example .env                             # add GROQ_API_KEY

# 3. Start backend
.venv/Scripts/uvicorn app.main:app --reload --port 8000

# 4. Frontend
cd ..
npm install
npm run dev   # Vite dev server at localhost:5173

# 5. Load extension in Chrome
# chrome://extensions → Developer mode → Load unpacked → dist/
npm run build  # builds to dist/
```

---

## Repository layout

```
mailmind/
├── backend/
│   ├── app/
│   │   ├── main.py                   FastAPI app + CORS
│   │   ├── models.py                 All Pydantic request/response models
│   │   ├── pipeline_agent.py         Phase 2 orchestrator (2-wave parallel)
│   │   ├── classification_agent.py   Classify → category + priority
│   │   ├── phishing_agent.py         Phishing / social-engineering detection
│   │   ├── action_agent.py           Meetings + tasks (internal parallel)
│   │   ├── reply_agent.py            Smart reply generation
│   │   ├── summary_agent.py          Bullet-point summariser (≥300 words)
│   │   ├── grammar_agent.py          Grammar / spelling checker
│   │   ├── tone_agent.py             Tone rewriter (6 styles)
│   │   ├── translate_agent.py        Email translation (5 languages)
│   │   ├── social_engineering.py     Rule-based trust scorer (no LLM)
│   │   ├── link_analyzer.py          Rule-based link risk extractor (no LLM)
│   │   ├── deadline_extractor.py     Rule-based deadline extractor (no LLM)
│   │   ├── chains/
│   │   │   ├── base.py               Groq LLM factory + multi-model cache
│   │   │   ├── classification_chain.py
│   │   │   ├── phishing_chain.py
│   │   │   ├── action_chain.py       (meeting extraction)
│   │   │   ├── task_chain.py
│   │   │   ├── reply_chain.py
│   │   │   ├── summary_chain.py
│   │   │   ├── grammar_chain.py
│   │   │   ├── tone_chain.py
│   │   │   └── translate_chain.py
│   │   └── routers/
│   │       ├── pipeline.py           POST /api/v1/pipeline
│   │       ├── classify.py
│   │       ├── phishing.py
│   │       ├── trust.py
│   │       ├── links.py
│   │       ├── actions.py
│   │       ├── replies.py
│   │       ├── summarize.py
│   │       ├── grammar.py
│   │       ├── tone.py
│   │       ├── translate.py
│   │       └── analyze.py            (Phase 1 legacy)
│   └── tests/
│       ├── test_classify_30.py       30-email accuracy benchmark (27/30 = 90%)
│       ├── test_actions_20.py        20-email action benchmark (20/20 = 100%)
│       ├── test_replies_15.py        15-email reply benchmark (15/15 = 100%)
│       ├── test_reply_quality.py     8-email reply text quality check
│       ├── test_phishing_fp.py       18-email FP check (0 false positives)
│       └── test_pipeline.py          3-email end-to-end pipeline check
├── src/
│   ├── content/
│   │   ├── content.ts                Gmail SPA observer; scrapes email data
│   │   └── compose.ts                Gmail compose body injection
│   ├── sidebar/
│   │   └── Sidebar.tsx               Main sidebar component + all sub-panels
│   └── lib/
│       └── api.ts                    Typed API client (all endpoints)
├── docs/
│   ├── api.md                        Full API reference (Phase 1 + 2)
│   ├── handoff.md                    This file
│   ├── classification.md             Classifier design notes
│   ├── action-schema.md              Action extraction schema reference
│   └── phase3-architecture.md        Phase 3 design plan
└── manifest.json                     Chrome MV3 manifest
```

---

## Architecture decisions

### LangChain LCEL chains (not raw OpenAI calls)

All LLM calls use LangChain `ChatPromptTemplate | ChatOpenAI | JsonOutputParser`  
wrapped with `.with_retry(stop_after_attempt=3)`. This gives:
- Automatic retry on LLM/network errors
- Lazy singleton chain instances (module-level `_chain` globals)
- Clean separation: chain files own prompt + parsing, agent files own business logic

**Gotcha:** JSON examples with `{key}` syntax in system prompts break LangChain's
template parser. Fix: always pass the system prompt as `SystemMessage(content=_SYSTEM)`
(a static object), not as a string in `from_messages([("system", ...)])`.

### Groq endpoint, two models

- `llama-3.1-8b-instant` (500k TPD, ~fast) — classification, phishing, actions, replies
- `llama-3.3-70b-versatile` (100k TPD, ~quality) — grammar, tone rewrite, translation, summarisation

The multi-model cache in `chains/base.py` keys instances by `(model, temperature, max_tokens)`
so agents with different requirements get their own `ChatOpenAI` instance.

### Pipeline parallelism

`pipeline_agent.py` runs six agents in two waves:

```
Wave 1 (start immediately, all in parallel):
  classify_email + detect_phishing + links/trust (sync, sub-ms)

  await classify_task → get category/priority

Wave 2 (start after classification):
  extract_actions + generate_replies (both use category context)

Final gather: phishing + risk + actions + replies
```

Wall-clock ≈ max(classify, phishing) + max(actions, replies) ≈ 2–4s on Groq free tier.

### Rule-based vs. LLM

Three modules deliberately avoid LLM calls:
- `link_analyzer.py` — regex-based URL risk extraction
- `social_engineering.py` — regex-based urgency + credential pattern matching
- `deadline_extractor.py` — regex + dateutil date resolution

These are synchronous, instant (< 5ms), and 100% deterministic.

### Gmail compose injection

`src/content/compose.ts` tries four CSS selectors in order, then uses
`execCommand('insertText')` with an `innerHTML` fallback for Gmail versions
that block `execCommand`.

### Smart replies: `reply_needed` flag

The reply chain returns `reply_needed: false` for automated notifications,
shipping confirmations, newsletters, and receipts. The sidebar shows a
"No reply needed" dismissal card instead of reply variants in this case.

---

## Running benchmarks

All benchmarks load `.env` manually (no FastAPI server required):

```bash
# From repo root:
python backend/tests/test_classify_30.py   # classification accuracy
python backend/tests/test_actions_20.py    # action extraction
python backend/tests/test_replies_15.py    # reply generation
python backend/tests/test_reply_quality.py # reply text quality
python backend/tests/test_phishing_fp.py   # phishing false positives
python backend/tests/test_pipeline.py      # end-to-end pipeline
```

**Benchmark results (July 2025):**

| Test | Result | Threshold |
|---|---|---|
| Classification accuracy (30 emails) | 27/30 = 90% | ≥ 90% |
| Action extraction (20 emails) | 20/20 = 100% | ≥ 85% |
| Reply benchmark (15 emails) | 15/15 = 100% | ≥ 87% |
| Reply quality (8 emails) | 0 failures | ≤ 1 |
| Phishing false positives (18 emails) | 0 FP | 0 |
| Pipeline structural check (3 emails) | 3/3 | 0 failures |

---

## Known boundary cases

**Classification:**
- "No action required" at email end → classifier correctly assigns `low` (not `normal`)
- "Blocking my workflow" bugs → classifier may assign `high` instead of `normal`
- Maintenance window notifications without strict personal deadlines → `normal` rather than `high`

**Phishing:**
- Aggressive legitimate marketing emails (urgency language, generic greeting) → `suspicious`
  with `risk_score < 0.5` and `safe_to_open = true` — correct behaviour

**Replies:**
- `[Your Name]` placeholder must be replaced by the user before sending
- `direct` tone variants are shorter; `formal` variants use full sign-offs

---

## Environment variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | From console.groq.com |
| `GROQ_MODEL` | No | `llama-3.1-8b-instant` | Override default 8b model |
| `CHROME_EXTENSION_ID` | No | — | Allows `chrome-extension://` CORS origin |
| `VITE_API_URL` | No | `http://localhost:8000` | Backend URL for Vite/extension build |
