# MailMind — Phase 2 Teammate Update

**Date:** July 2025  
**Branch:** master  
**Status:** Phase 2 complete ✓

---

## What shipped in Phase 2

### 1. Classification engine

Every email is now classified into one of 8 categories (meeting, complaint, job, update,
invoice, support, social, spam) and one of 4 priority levels (urgent, high, normal, low).

- `POST /api/v1/classify` returns `category`, `priority`, `confidence`, `reason`
- Priority uses strict decision rules (urgent = same-day irreversible, high = 24–48h, etc.)
- **Accuracy: 27/30 = 90%** on 30-email benchmark across all categories and priority levels
- The classifier correctly handles edge cases: CVE advisories → `update`, spear-phishing-style IT emails → `support`/`update`, newsletters with "URGENT" subject lines → `spam/low`

### 2. Phishing + social-engineering detection

- `POST /api/v1/phishing` returns verdict, risk score, active indicators, explanation, safe_to_open
- 10 indicator classes: urgency pressure, sender mismatch, lookalike domain, suspicious links, credential request, prize scam, impersonation, generic greeting, grammar errors, attachment bait
- **False positive rate: 0/18** on 18-email legitimate-email check
- Legitimate marketing emails are correctly rated `suspicious` (not `phishing`) with `safe_to_open = true`

### 3. Rule-based trust scoring + link analysis

- `POST /api/v1/trust` — composite trust score 0–100 with breakdown by risk type
- `POST /api/v1/links` — per-URL risk flags: shortened URL, domain mismatch, brand mismatch, raw IP, redirect param
- Both are synchronous, no LLM, respond in < 10ms

### 4. Action extraction

- `POST /api/v1/actions` extracts meetings, deadlines, and tasks from a single email
- Meeting and task LLM calls run in parallel internally (`asyncio.gather`)
- Deadlines extracted rule-based (deterministic)
- **Accuracy: 20/20 = 100%** on 20-email benchmark

### 5. Smart replies

- `POST /api/v1/replies` generates 2–3 reply variants with distinct intents
- Each variant has a `label`, `tone` (formal/friendly/direct), and complete ready-to-send `text`
- `reply_needed: false` returned for automated notifications — sidebar shows dismissal card
- **Accuracy: 15/15 = 100%** on 15-email benchmark; **8/8** quality checks pass
- "Insert into compose" injects text directly into Gmail's contenteditable compose window
- "Edit before sending" mode: inline textarea before insertion

### 6. Unified pipeline endpoint

- `POST /api/v1/pipeline` runs all 6 agents with optimised parallelism in 2 waves:
  - Wave 1: classification + phishing + trust/links (all start simultaneously)
  - Wave 2: actions + replies (start after classification provides category context)
- Single call replaces 5+ individual calls from the frontend
- Returns `elapsed_ms` for performance monitoring

### 7. LangChain LCEL migration

All LLM agents now use LangChain `ChatPromptTemplate | ChatOpenAI | JsonOutputParser`
chains with `.with_retry(stop_after_attempt=3)`. No more raw `openai_client.py` usage
in any agent. The multi-model cache (`chains/base.py`) handles different temperature
and max_tokens requirements per agent cleanly.

---

## Key numbers

| Metric | Value |
|---|---|
| New API endpoints | 7 (classify, phishing, trust, links, actions, replies, pipeline) |
| Total endpoints | 13 |
| LLM model calls (per pipeline) | 5 (classify, phishing, action, task, reply) |
| Rule-based calls (per pipeline) | 2 (links, trust) |
| Pipeline wall-clock (Groq free tier) | ~3–5s typical |
| Test coverage | 6 benchmarks, 96 test emails total |

---

## What's NOT in Phase 2

- Summarisation, grammar, tone rewrite, translate — these were Phase 1 and remain
  available as individual endpoints; they are not part of the pipeline call
- Email sending — sidebar can only insert text into the Gmail compose window
- Thread history — sidebar resets per email (Phase 3 scope)
- User settings persistence — Phase 3 scope

---

## Files changed (significant)

**New agents:** `pipeline_agent.py`  
**New chains:** `tone_chain.py`, `translate_chain.py`, `summary_chain.py`, `grammar_chain.py`  
**Updated agents:** `summary_agent.py`, `grammar_agent.py`, `tone_agent.py`, `translate_agent.py` (all now delegate to chains)  
**New routers:** `pipeline.py`, `replies.py`, `actions.py`, `classify.py`, `phishing.py`  
**New models:** `PipelineRequest`, `PipelineResponse`, `ReplyRequest`, `ReplyResponse`, `ReplyVariant`, `ActionResponse` (+ submodels)  
**Frontend new:** `src/content/compose.ts`, `src/lib/api.ts` (extended with all Phase 2 types)  
**Frontend updated:** `src/sidebar/Sidebar.tsx` (ClassificationBadge, SuggestedActions, SmartReplies components)  
**Tests:** 6 benchmark files in `backend/tests/`  
**Docs:** `docs/api.md` (full rewrite), `docs/handoff.md` (updated), `docs/phase3-architecture.md` (new)

---

## Demo video

> **TODO:** Record a 3–5 minute walkthrough of the Phase 2 sidebar:
> 1. Open a meeting invite → show classification badge + action extraction
> 2. Open a phishing email → show risk banner + indicator chips
> 3. Open a task email → show smart reply variants, insert one into compose
> 4. Show the pipeline timing in DevTools Network tab

Screen recording: use Loom or OBS. Share the link in `#mailmind` Slack channel.

---

## Phase 3 is next

See `docs/phase3-architecture.md` for the full plan. Top priorities:

1. **Skeleton loading** — perceived latency before SSE streaming
2. **Phishing risk banner** — safety-critical, high user value
3. **Actions board** — Kanban layout + ICS calendar export
4. **Smart replies 2.0** — name personalisation, reply history
5. **SSE streaming pipeline** — render sections as they arrive
