# MailMind — Phase 1 Teammate Handoff

This document gives a new contributor enough context to run the project, understand the
key design decisions, and pick up Phase 2 work without reading every file.

---

## What the project is

MailMind is a Chrome MV3 extension that injects a sidebar into Gmail and surfaces AI-powered
insights about the open email: an analysis summary, action items, quick replies, grammar
corrections, tone rewrites, translation, and (for long emails) a bullet-point summary.

The extension communicates with a local FastAPI backend. The backend calls Groq's LLM API.
No email content ever reaches a third-party server except Groq (which you control via your
own API key).

---

## Repository layout

```
mailmind/
├── src/                      Chrome extension (React 18 + TypeScript + Tailwind)
│   ├── content.ts            Injected into Gmail; detects open email, posts to sidebar
│   ├── background.ts         MV3 service worker
│   ├── popup/                Extension popup (minimal, links to sidebar)
│   ├── sidebar/
│   │   └── Sidebar.tsx       Main UI component (~500 lines)
│   └── lib/
│       ├── api.ts            All fetch calls to the backend (typed)
│       ├── usePrivacyMode.ts Hook — reads/writes chrome.storage.sync
│       └── __tests__/        Vitest unit tests for the hook
├── backend/
│   ├── app/
│   │   ├── main.py           FastAPI app + CORS config
│   │   ├── models.py         Pydantic request/response models
│   │   ├── openai_client.py  Groq client singleton
│   │   ├── routers/          One file per endpoint
│   │   ├── grammar_agent.py  LLM call for grammar correction
│   │   ├── tone_agent.py     LLM call for tone rewrite
│   │   ├── translate_agent.py LLM call for translation
│   │   └── summary_agent.py  LLM call for bullet summarisation
│   └── tests/
│       ├── conftest.py       Shared fixtures + mock patch setup
│       ├── test_analyze.py
│       ├── test_grammar.py
│       ├── test_tone.py
│       ├── test_translate.py
│       ├── test_summarize.py
│       └── test_integration.py  Cross-feature, multi-persona integration tests
├── docs/
│   ├── api.md                Full API reference (start here for endpoint details)
│   └── handoff.md            This file
└── manifest.json             Chrome MV3 manifest
```

---

## Local dev setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- A Groq API key ([console.groq.com](https://console.groq.com))
- Chrome (or Chromium)

### Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt

# Create .env (never commit this file)
echo "GROQ_API_KEY=gsk_..." > .env
# Optional: also add CHROME_EXTENSION_ID=abc123... for CORS

uvicorn app.main:app --reload
# → http://localhost:8000
# → http://localhost:8000/docs  (interactive Swagger UI)
```

### Extension

```bash
# From repo root
npm install
npm run dev
# Vite/CRXJS rebuilds on save; the dist/ folder is updated live.
```

Load the extension in Chrome:

1. Open `chrome://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked** → select the `dist/` folder
4. Open [mail.google.com](https://mail.google.com) and click any email

### Running tests

```bash
# Backend (225 tests)
cd backend
.venv\Scripts\python.exe -m pytest -v

# Frontend (10 tests)
npm test
```

---

## Key design decisions

### Why a local backend instead of calling Groq from the extension?

API keys cannot be embedded in a Chrome extension — the manifest and source are readable
by anyone who installs it. The local backend keeps the key server-side and provides a
validation + normalisation layer that the raw LLM output can't guarantee.

### Privacy mode (Off / Manual / Smart)

Three modes stored in `chrome.storage.sync` so they persist across browser restarts and
sync across devices:

- **Off** — no email content is ever sent to the backend. The sidebar shows a prompt to
  change mode.
- **Manual** — analysis only runs when the user clicks "Analyse". Nothing auto-fires.
- **Smart** — analysis runs automatically when a new email opens.

The mode is enforced in `Sidebar.tsx` via three `useEffect` hooks:
1. Reads mode from storage on mount; subscribes to `chrome.storage.onChanged`.
2. Auto-fires analysis when `emailData` changes — only when mode is `"smart"`.
3. Cancels any in-flight request when mode switches to `"off"`.

In-flight cancellation uses a `cancelRef` pattern (a `useRef` holding a `() => void`
cancel function) rather than `AbortController` — simpler and sufficient for a single
concurrent call.

### Why `data.get("field") or []` instead of `data.get("field", [])`?

The LLM can return `{"action_items": null}`. `dict.get("key", [])` returns `None` here
because the key *is* present; `or []` handles both missing and `null` in one expression.
See `routers/analyze.py` and `routers/grammar.py`.

### Sentiment/tone normalisation

The LLM prompt constrains the values, but any output outside the declared enum is silently
normalised to `"neutral"` / `"formal"`. This prevents the frontend from ever receiving an
unexpected string. `frozenset` is used for O(1) membership checks.

### Input truncation

Every agent caps its input before the LLM call:
- `grammar_agent.py`: 4 000 chars
- `summary_agent.py`: 4 000 chars
- `tone_agent.py`: 2 000 chars (shorter because tone rewrites are returned in full)
- `translate_agent.py`: its own cap (see source)

The summarise endpoint also skips the LLM entirely for emails under 300 words
(`LONG_EMAIL_THRESHOLD_WORDS`), returning `was_summarized: false` with zero latency.

### Test mocking strategy

All tests patch at the **point of use** (the imported name inside the router module), not
at the definition site. This is the correct pattern for `unittest.mock.patch` with Python
imports. The `conftest.py` `autouse` fixture applies all patches to every test in the suite.
Frontend tests use `vi.stubGlobal('chrome', chromeMock)` — vitest's equivalent.

---

## Current state at Phase 1 handoff

**Backend:** 225 tests, 0 failures.  
**Frontend:** 10 tests, 0 failures, 0 TypeScript errors.

All Phase 1 endpoints are shipped and tested:

| Endpoint | Status |
|----------|--------|
| `GET /health` | ✓ |
| `POST /api/v1/analyze` | ✓ |
| `POST /api/v1/grammar` | ✓ |
| `POST /api/v1/rewrite-tone` | ✓ |
| `POST /api/v1/translate` | ✓ |
| `POST /api/v1/summarize` | ✓ |

The sidebar renders all features. Privacy mode is enforced end-to-end.

---

## Known constraints and gotchas

- **Backend must be running locally.** There is no deployed backend. If the user stops the
  uvicorn process, all AI features silently fail (the sidebar shows an error state).
- **Groq rate limits.** The free tier allows ~30 requests/minute. Rapid email switching
  in Smart mode can hit this. Phase 2 should add request debouncing or a queue.
- **CORS in production.** `CHROME_EXTENSION_ID` must be set in `.env` to allow requests
  from the installed extension in production. The extension ID changes on every unpacked
  reload; only packed/published extensions have stable IDs.
- **SPA navigation in Gmail.** Gmail is a single-page app. The content script uses
  `MutationObserver` to detect email opens. If Gmail changes its DOM structure, the
  detection may break.
- **`chrome.storage.sync` quota.** The quota is 100 KB total / 8 KB per item. Currently
  only `privacyMode` is stored, which is well within limits.

---

## Suggested Phase 2 work

- **Smart compose integration** — intercept Gmail's compose window and offer real-time
  tone/grammar suggestions as the user types.
- **Request debouncing** — add a 500 ms debounce before firing analysis in Smart mode to
  avoid hammering Groq on rapid email switches.
- **Streaming responses** — switch tone/grammar endpoints to server-sent events so the
  rewritten text streams into the sidebar word-by-word instead of appearing all at once.
- **Deployed backend** — containerise and deploy the FastAPI app so users do not need to
  run a local server. This requires a secrets management strategy (not env files).
- **Thread context** — pass the full reply thread to the analyse endpoint so quick replies
  are contextually aware of the conversation history.
- **Offline mode** — cache the last analysis per email ID in `chrome.storage.local` so the
  sidebar shows stale-but-useful data when the backend is unreachable.
