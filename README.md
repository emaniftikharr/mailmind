# MailMind

AI-powered Gmail sidebar that analyses your emails as you read them. Built as a Chrome MV3
extension with a local FastAPI backend and Groq LLM.

---

## Phase 1 features

| Feature | What it does |
|---------|-------------|
| **Email analysis** | 2–3 sentence summary, action items, quick-reply suggestions, sentiment, and tone detected automatically |
| **Grammar check** | Full correction with per-change explanations; shows original vs corrected side-by-side |
| **Tone rewrite** | Rewrites your email in Formal, Friendly, Concise, Persuasive, Executive, or Professional style |
| **Translation** | Translates email body to Spanish, French, German, Portuguese, or Japanese |
| **Smart summary** | Condenses emails over 300 words into 3–5 bullet points; includes "Show full email" toggle |
| **Privacy mode** | Off / Manual / Smart — controls when (or whether) email content is sent to the backend |

---

## Architecture

```
Gmail (browser)
  └── content script          detects open email via MutationObserver
        └── React sidebar     renders analysis panels, manages privacy mode
              │
              │  fetch (JSON)
              ▼
      FastAPI backend          localhost:8000
        ├── /api/v1/analyze
        ├── /api/v1/grammar
        ├── /api/v1/rewrite-tone
        ├── /api/v1/translate
        └── /api/v1/summarize
              │
              │  OpenAI-compatible API
              ▼
          Groq  (llama-3.3-70b-versatile)
```

Email content stays on your machine. The only external call is to Groq using your own API key.

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- Chrome or Chromium
- [Groq API key](https://console.groq.com)

---

## Quick start

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

Create `backend/.env`:

```
GROQ_API_KEY=gsk_your_key_here
```

Start the server:

```bash
uvicorn app.main:app --reload
```

The API is now at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### 2. Extension

```bash
# From repo root
npm install
npm run dev
```

Load into Chrome:

1. Go to `chrome://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked** → select the `dist/` folder
4. Open [Gmail](https://mail.google.com) and click any email

---

## Development commands

| Command | What it does |
|---------|-------------|
| `npm run dev` | Build extension with hot reload |
| `npm run build` | Production build |
| `npm test` | Run frontend unit tests (vitest) |
| `cd backend && uvicorn app.main:app --reload` | Start backend with auto-reload |
| `cd backend && .venv\Scripts\python.exe -m pytest -v` | Run all 225 backend tests |

---

## Privacy mode

The sidebar has three modes, persisted in `chrome.storage.sync`:

- **Off** — no email content leaves the browser. All AI panels are hidden.
- **Manual** — analysis runs only when you click the Analyse button.
- **Smart** — analysis fires automatically when you open an email.

The default is Smart. Change it with the toggle at the top of the sidebar.

---

## Project structure

```
src/                   Chrome extension source
  content.ts           Gmail DOM injection + email detection
  background.ts        MV3 service worker
  sidebar/
    Sidebar.tsx        Main UI (privacy mode, all feature panels)
  lib/
    api.ts             Typed fetch wrappers for all backend endpoints
    usePrivacyMode.ts  chrome.storage hook (independently testable)
backend/
  app/
    main.py            FastAPI app entry point
    models.py          Pydantic request/response schemas
    routers/           One router per endpoint
    *_agent.py         LLM prompt logic for each feature
  tests/               225 tests (unit + integration)
docs/
  api.md               Full endpoint reference with request/response shapes
  handoff.md           Architecture notes and contributor guide
```

---

## API reference

See [docs/api.md](docs/api.md) for the full contract for each endpoint, including all
request fields, response shapes, enum values, error codes, and edge-case behaviour.

---

## Contributor notes

See [docs/handoff.md](docs/handoff.md) for architecture decisions, test strategy, known
constraints, and suggested Phase 2 work.
