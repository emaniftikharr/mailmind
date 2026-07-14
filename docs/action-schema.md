# Action Extraction — Output Schema

`POST /api/v1/actions` extracts meetings, deadlines, and tasks from an email.
Deadline extraction is rule-based (always succeeds). Meeting and task extraction
use an LLM (llama-3.1-8b-instant via Groq) with safe fallbacks on failure.

---

## Request

```json
{
  "subject": "Q3 Strategy Meeting - Thursday at 2 PM",
  "body":    "Hi team, you are invited to the Q3 Strategy Meeting on Thursday...",
  "sender":  "sarah@company.com"
}
```

| Field     | Type   | Required | Notes                                        |
|-----------|--------|----------|----------------------------------------------|
| `subject` | string | no       | Email subject line; defaults to `""`         |
| `body`    | string | yes      | Email body text; min length 1                |
| `sender`  | string | no       | Sender address for organizer hints; defaults to `""` |

Input is truncated to 3,000 characters before LLM calls to control latency.

---

## Response — `ActionResponse`

```json
{
  "meeting":      { ... },
  "deadlines":    [ ... ],
  "tasks":        [ ... ],
  "has_meeting":  true,
  "has_deadlines": true,
  "has_tasks":    true
}
```

| Field          | Type            | Description                              |
|----------------|-----------------|------------------------------------------|
| `meeting`      | `MeetingModel`  | Always present (fallback if LLM fails)   |
| `deadlines`    | `DeadlineModel[]` | Empty list if no deadlines detected    |
| `tasks`        | `TaskModel[]`   | Empty list if no tasks detected          |
| `has_meeting`  | boolean         | `meeting.meeting_detected`               |
| `has_deadlines`| boolean         | `len(deadlines) > 0`                     |
| `has_tasks`    | boolean         | `len(tasks) > 0`                         |

---

## `MeetingModel`

Extracted by LLM from meeting invites, scheduling requests, calendar items.

```json
{
  "meeting_detected": true,
  "title":            "Q3 Strategy Meeting",
  "date_str":         "Thursday, July 17",
  "time_str":         "2:00 PM",
  "duration_minutes": 90,
  "location":         "Conference Room B",
  "organizer":        "sarah@company.com",
  "attendees":        ["team"],
  "agenda":           "Q2 review, Q3 OKRs, budget allocation",
  "is_tentative":     false,
  "extraction_error": null
}
```

| Field              | Type          | Values / Notes                                      |
|--------------------|---------------|-----------------------------------------------------|
| `meeting_detected` | boolean       | `true` only when a real meeting/call is present     |
| `title`            | string        | Event title; `""` when no meeting                   |
| `date_str`         | string        | Raw date text from email (not ISO-normalized)       |
| `time_str`         | string        | Raw time text from email (not ISO-normalized)       |
| `duration_minutes` | integer\|null | Estimated or stated duration; `null` if unknown     |
| `location`         | string        | Room, address, or URL; `""` if unspecified          |
| `organizer`        | string        | Sender or named organizer; `""` if unclear          |
| `attendees`        | string[]      | Named attendees; may be `["team"]` for group invites|
| `agenda`           | string        | Meeting agenda or purpose; `""` if none             |
| `is_tentative`     | boolean       | `true` for "are you free?" / tentative proposals    |
| `extraction_error` | string\|null  | Set on LLM failure; meeting values are fallback defaults |

### `meeting_detected` = false

When no meeting is present, `meeting_detected` is `false` and all other fields
are empty strings / defaults. `extraction_error` is `null` unless the LLM call
itself failed (in which case both `meeting_detected` and `extraction_error` will
be set).

---

## `DeadlineModel`

Extracted by rule-based pattern matching (no LLM). Zero false positives on
meeting-language ("the meeting is on Tuesday").

```json
{
  "phrase":        "by Friday EOD",
  "resolved_date": "2026-07-17",
  "confidence":    "high",
  "is_relative":   true,
  "urgency":       "this_week"
}
```

| Field           | Type          | Values / Notes                                   |
|-----------------|---------------|--------------------------------------------------|
| `phrase`        | string        | Exact text matched from the email                |
| `resolved_date` | string\|null  | ISO 8601 date (`"YYYY-MM-DD"`); `null` for ASAP  |
| `confidence`    | string        | `"high"` / `"medium"` / `"low"`                  |
| `is_relative`   | boolean       | `true` for "by Friday"; `false` for "August 1"  |
| `urgency`       | string        | See urgency levels below                         |

### Urgency levels

| Value        | Meaning                                  |
|--------------|------------------------------------------|
| `"overdue"`  | Resolved date is in the past             |
| `"today"`    | Due today                                |
| `"tomorrow"` | Due tomorrow                             |
| `"this_week"`| Due within the current week              |
| `"next_week"`| Due next calendar week                   |
| `"this_month"`| Due this month                          |
| `"future"`   | Due more than a month away               |
| `"asap"`     | No resolvable date; "ASAP" / "immediately"|

### Pattern categories

**Requires deadline indicator** (`by` / `due` / `before` / `deadline` / `no later than`):
relative weekdays, "tomorrow", "next week", "end of month", "within N days/weeks",
absolute dates (month-day, numeric formats).

**Self-contained** (no indicator needed):
"ASAP", "EOD" / "COB" (today), "EOW" / "end of week", "EOM" / "end of month".

---

## `TaskModel`

Extracted by LLM. Identifies action items that the **recipient** must do,
as well as significant commitments the **sender** made.

```json
{
  "title":        "Send Q3 sales report",
  "description":  "Recipient was asked to send the Q3 sales report for a board presentation",
  "assignee":     "me",
  "due_date_str": "by Friday",
  "priority":     "high"
}
```

| Field          | Type   | Values / Notes                                      |
|----------------|--------|-----------------------------------------------------|
| `title`        | string | Concise imperative phrase, ≤ 8 words                |
| `description`  | string | One-sentence context summary                        |
| `assignee`     | string | `"me"` / `"them"` / `"other"` — see below          |
| `due_date_str` | string | Raw deadline text from email; `""` if unspecified   |
| `priority`     | string | `"urgent"` / `"high"` / `"normal"` / `"low"`       |

### Assignee values

| Value    | Meaning                                               |
|----------|-------------------------------------------------------|
| `"me"`   | The **recipient** must do this                        |
| `"them"` | The **sender** committed to do this ("I'll send you…")|
| `"other"`| A third party is responsible, or unclear              |

Only `assignee="them"` and `"other"` tasks that are significant follow-up items
(e.g., deliverables the recipient should track) are included. Purely informational
sentences are omitted.

### Priority mapping

| Value      | Trigger                                               |
|------------|-------------------------------------------------------|
| `"urgent"` | Same-day deadline, "ASAP", "immediately"              |
| `"high"`   | 1–2 day window, or explicitly "important" / "urgent"  |
| `"normal"` | Within a week, or no stated time pressure             |
| `"low"`    | "Whenever you get a chance", "no rush"                |

---

## Full example — mixed email (meeting + deadline + task)

### Request

```json
{
  "subject": "Kickoff meeting July 20 - agenda due July 18",
  "body": "Team, project kickoff is set for Monday July 20 at 10 AM via Zoom. Please submit your agenda items by Friday July 18 so I can compile the final agenda. The session will be 2 hours. All team leads are required to attend.",
  "sender": "pm@company.com"
}
```

### Response

```json
{
  "meeting": {
    "meeting_detected": true,
    "title": "Project Kickoff",
    "date_str": "Monday July 20",
    "time_str": "10 AM",
    "duration_minutes": 120,
    "location": "Zoom",
    "organizer": "pm@company.com",
    "attendees": ["team leads"],
    "agenda": "Project kickoff",
    "is_tentative": false,
    "extraction_error": null
  },
  "deadlines": [
    {
      "phrase": "by Friday July 18",
      "resolved_date": "2026-07-18",
      "confidence": "high",
      "is_relative": false,
      "urgency": "this_week"
    }
  ],
  "tasks": [
    {
      "title": "Submit agenda items",
      "description": "Submit agenda items by July 18 for the project kickoff meeting",
      "assignee": "me",
      "due_date_str": "by Friday July 18",
      "priority": "high"
    }
  ],
  "has_meeting": true,
  "has_deadlines": true,
  "has_tasks": true
}
```

---

## Error handling

| Scenario                  | Behavior                                                |
|---------------------------|---------------------------------------------------------|
| LLM meeting call fails    | `meeting_detected=false`, `extraction_error=<message>` |
| LLM task call fails       | `tasks=[]`, `has_tasks=false`                           |
| Both LLM calls fail       | Both fallbacks active; `deadlines` still populated      |
| Input exceeds 3,000 chars | Input truncated before LLM calls; deadlines use full text|
| No deadlines in email     | `deadlines=[]`, `has_deadlines=false`                   |

Meeting and task LLM calls run in **parallel** (`asyncio.gather`) to minimize
wall-clock latency. Each is independently protected by a try/except fallback
and retried up to 3 times on transient errors.
