# MailMind — Phase 3 Visual Architecture

## Goal

Surface the Phase 2 intelligence visually in a polished, production-ready sidebar
that works reliably across all Gmail views. Phase 3 is about UI quality,
user workflow, and the first features that work with the user's data over time.

---

## What Phase 2 gave us (inputs to Phase 3)

Every email now produces a `PipelineResponse` containing:

```
classification  category + priority + confidence
phishing        verdict + risk_score + indicators
trust           trust_score (0-100) + risk_level
links           per-URL risk flags
actions         meeting + deadlines + tasks
replies         2-3 variants with tone + insert button
```

Phase 3 turns these raw outputs into a cohesive UI with state, history, and user preferences.

---

## Feature roadmap

### 3.1 — Sidebar visual overhaul

**Priority gauge** — replace the text badge with a colour-coded pill + animated border:

```
┌─────────────────────────────────────────┐
│  ● URGENT  complaint  conf 0.99         │  ← red border pulse
│  ─────────────────────────────────────  │
│  Risk: ████████░░ 78 / MODERATE         │  ← trust score bar
└─────────────────────────────────────────┘
```

**Collapsible sections** — each panel (Phishing, Actions, Replies) collapses to a
one-line summary chip. User state persists across email switches via `chrome.storage.local`.

**Skeleton loading** — show shimmer placeholders during the pipeline call instead of
blank space. Each section animates in as its data arrives.

### 3.2 — Phishing + Trust visual

**Risk banner** — shown above all other content when `phishing.verdict = 'phishing'`
or `trust.risk_level = 'critical'`:

```
┌──────────────────────────────────────────┐
│ ⚠  PHISHING DETECTED  risk 0.97          │  red background
│    lookalike_domain · credential_request  │
│    Do not click links or reply.           │
└──────────────────────────────────────────┘
```

**Indicator chips** — each phishing indicator displayed as a coloured chip with a
tooltip showing the indicator definition. Click → highlights the relevant span in
the email body using the Gmail DOM (future: Phase 3.4).

**Link table** — expandable section listing all extracted links. Flagged links shown
in amber/red; clean links in grey. "Copy safe link" button strips redirect parameters.

### 3.3 — Actions board

Replace the current flat list with a Kanban-style three-column layout:

```
┌─────────────┬──────────────┬──────────────┐
│  MEETINGS   │  DEADLINES   │    TASKS     │
│─────────────│──────────────│──────────────│
│ Thu Jul 17  │ ⚡ Today      │ ☐ Confirm    │
│ 2 PM        │  EOD patch   │   attendance │
│ Room B      │              │              │
│             │ 📅 Wed Jul 16 │ ☐ Review     │
│ [Add to Cal]│  Reply by    │   Section 3  │
└─────────────┴──────────────┴──────────────┘
```

- **"Add to Calendar"** button: generates a `data:text/calendar` ICS file and triggers download
- **Task checkboxes**: persist checked state in `chrome.storage.local` keyed by message ID
- **Deadline urgency icons**: ⚡ today, 🔥 tomorrow, 📅 this week, 🗓 future

### 3.4 — Smart replies 2.0

**"Use this reply" flow:**

1. User clicks "Use this reply"
2. Reply text inserts into compose (existing `insertIntoCompose`)
3. Sidebar shows a "Reply sent?" prompt with Undo button for 5 seconds
4. After send, sidebar resets and re-runs pipeline on the sent message thread

**Personalisation panel:**
- User sets their name once → stored in `chrome.storage.sync`
- `[Your Name]` placeholder replaced automatically on insert

**Reply history:** Last 5 inserted replies stored per-thread. Shown as chips at top of
SmartReplies panel. One-click re-insert any previous variant.

### 3.5 — Settings panel

Accessed via ⚙ icon in sidebar header:

```
┌─────────────────────────────────┐
│  MailMind Settings              │
│  ───────────────────────────    │
│  Your name  [Alex Johnson    ]  │
│                                 │
│  Default tone  ● Formal         │
│                ○ Friendly       │
│                ○ Direct         │
│                                 │
│  Privacy mode  [toggle]         │
│  Show risk banner  [toggle]     │
│  Auto-expand actions  [toggle]  │
└─────────────────────────────────┘
```

All settings stored in `chrome.storage.sync` (syncs across user's Chrome profiles).

### 3.6 — Thread awareness

Currently the sidebar resets on every navigation. Phase 3.6 adds thread awareness:

- Parse Gmail thread ID from the URL (`#inbox/thread-id`)
- Cache the `PipelineResponse` per thread ID in `chrome.storage.session`
- Show a "Refreshing…" indicator only when the open message changes within the thread
- Display conversation length chip: "3 messages in thread"

### 3.7 — Offline / error states

| State | What to show |
|---|---|
| Backend unreachable | "MailMind offline — start the backend server" with retry button |
| Pipeline timeout (> 10s) | Partial results shown; missing sections show skeleton + "Loading…" |
| LLM rate limit (502) | Toast: "AI temporarily unavailable — retrying…"; auto-retry after 5s |
| Privacy mode on | All panels hidden; single "Privacy mode active" chip |

---

## Technical decisions for Phase 3

### Streaming pipeline results

Instead of awaiting the full `PipelineResponse`, switch to Server-Sent Events (SSE):

```
POST /api/v1/pipeline/stream
→ Content-Type: text/event-stream

data: {"section":"classification","data":{...}}
data: {"section":"phishing","data":{...}}
data: {"section":"trust","data":{...}}
data: {"section":"links","data":{...}}
data: {"section":"actions","data":{...}}
data: {"section":"replies","data":{...}}
data: {"section":"done","elapsed_ms":1843}
```

Frontend renders each section as its data arrives. Classification + trust render first
(fastest), replies render last. Perceived latency drops from ~3s to ~0.5s.

**Backend:** `fastapi.responses.StreamingResponse` + `asyncio.Queue` with one producer
(pipeline agent) and one consumer (SSE formatter).

**Frontend:** `EventSource` in a background service worker relayed to the sidebar via
`chrome.runtime.sendMessage`.

### State management

Phase 3 introduces enough shared state that a single `usePipelineStore` Zustand store
(or React Context) should replace the current prop-drilling in `Sidebar.tsx`:

```typescript
interface PipelineStore {
  emailData: EmailData | null
  result: PipelineResponse | null
  status: 'idle' | 'loading' | 'partial' | 'done' | 'error'
  userSettings: UserSettings
  checkedTasks: Record<string, boolean>   // keyed by messageId + taskTitle
  insertedReplyIdx: number | null
}
```

### ICS calendar export

```typescript
// Generates RFC 5545 compliant .ics from a MeetingModel
function meetingToIcs(meeting: MeetingModel): string {
  return [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'BEGIN:VEVENT',
    `SUMMARY:${meeting.title}`,
    `DTSTART:${isoToIcs(meeting.date_str, meeting.time_str)}`,
    `DURATION:PT${meeting.duration_minutes ?? 60}M`,
    `LOCATION:${meeting.location}`,
    'END:VEVENT',
    'END:VCALENDAR',
  ].join('\r\n')
}
```

---

## Phase 3 delivery order

| Sprint | Features | Why this order |
|---|---|---|
| 3.1 | Skeleton loading + collapsible sections | Unblocks perceived performance before streaming |
| 3.2 | Phishing/trust risk banner + indicator chips | Safety-critical, highest user value |
| 3.3 | Actions board + ICS export | High utility, self-contained |
| 3.4 | Smart replies 2.0 + name personalisation | Builds on existing insert flow |
| 3.5 | Settings panel | Needed by 3.4 (name) and subsequent features |
| 3.6 | Thread awareness + session cache | Performance; reduces redundant API calls |
| 3.7 | Offline / error states | Polish; makes product feel reliable |
| 3.8 | SSE streaming pipeline | Architecture lift; do last when UI is stable |

---

## What NOT to build in Phase 3

- **Email sending** — Chrome MV3 CSP and Gmail API OAuth are out of scope; "insert into compose" is the right boundary
- **Email storage / history** — GDPR surface; `chrome.storage` session cache (3.6) is sufficient
- **Fine-tuning** — Groq's hosted models are adequate; fine-tuning adds infra complexity without clear accuracy gain at this stage
- **Multi-account Gmail** — Deferred; the sidebar assumes one active Gmail session
