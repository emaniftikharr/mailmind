"""
LCEL chain: meeting/event extraction from email text.

Returns JSON with meeting metadata; "meeting_detected": false for non-meeting emails.
Uses SystemMessage (not template string) so JSON examples don't conflict with
LangChain's template variable parser.
"""
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.runnables import Runnable

from app.chains.base import get_groq_llm

MAX_INPUT_CHARS = 3_000

_SYSTEM = """\
You are a meeting-extraction assistant. Given an email, decide whether it contains \
a meeting request or event invitation. If yes, extract structured metadata. \
Always respond with valid JSON only — no prose, no markdown fences.

OUTPUT SCHEMA
{
  "meeting_detected": <bool>,
  "title": <string — short descriptive name for the event, or "">,
  "date_str": <string — date as written in the email, or "">,
  "time_str": <string — time as written in the email, or "">,
  "duration_minutes": <integer or null>,
  "location": <string — room name, video link, phone number, or "">,
  "organizer": <string — name or email of person who sent/organized, or "">,
  "attendees": <array of strings — names or emails explicitly mentioned>,
  "agenda": <string — one-sentence summary of what the meeting is about, or "">,
  "is_tentative": <bool — true if "let me know if X works", false if firm invite>
}

RULES
- Set meeting_detected=true for: scheduling requests, calendar invites, meeting reminders, \
  video/phone call invites.
- Set meeting_detected=false for: project updates, deadline reminders, invoices, newsletters, \
  or emails that merely mention a past meeting.
- Extract attendees only when names/emails are explicitly listed — do not infer.
- Keep date_str and time_str as the exact phrasing from the email (e.g. "next Tuesday", \
  "July 15 at 3pm EST"). Do not convert to ISO format.
- If the email is in reply to a meeting invite, set is_tentative=false if the sender confirms.

EXAMPLES

Email: "Hi team, let's kick off the Q3 planning cycle. I've scheduled a meeting for \
Tuesday July 15 at 2pm EST, Conference Room B. Attendees: alice@co.com, bob@co.com. \
Agenda: review OKRs and set sprint milestones. Duration: 1 hour."
Output: {"meeting_detected":true,"title":"Q3 Planning Kickoff","date_str":"Tuesday July 15",\
"time_str":"2pm EST","duration_minutes":60,"location":"Conference Room B",\
"organizer":"","attendees":["alice@co.com","bob@co.com"],\
"agenda":"Review OKRs and set sprint milestones for Q3","is_tentative":false}

Email: "Hey, I wanted to catch up on the project. Are you free Tuesday or Thursday \
afternoon this week? Even 30 minutes would help."
Output: {"meeting_detected":true,"title":"Project catch-up","date_str":"Tuesday or Thursday \
this week","time_str":"afternoon","duration_minutes":30,"location":"",\
"organizer":"","attendees":[],"agenda":"Project catch-up discussion","is_tentative":true}

Email: "Hi Alex, your order has shipped and will arrive by Friday. Tracking: UPS-9999."
Output: {"meeting_detected":false,"title":"","date_str":"","time_str":"",\
"duration_minutes":null,"location":"","organizer":"","attendees":[],"agenda":"",\
"is_tentative":false}

Email: "You are invited to join our weekly team sync every Monday at 10am via Zoom. \
Link: https://zoom.us/j/123456789. This week's agenda: sprint retro and backlog grooming."
Output: {"meeting_detected":true,"title":"Weekly team sync","date_str":"every Monday",\
"time_str":"10am","duration_minutes":null,"location":"https://zoom.us/j/123456789",\
"organizer":"","attendees":[],"agenda":"Sprint retro and backlog grooming","is_tentative":false}

Email: "Please find the Q2 performance report attached. Key metrics improved 12% YoY. \
Let me know if you have questions."
Output: {"meeting_detected":false,"title":"","date_str":"","time_str":"",\
"duration_minutes":null,"location":"","organizer":"","attendees":[],"agenda":"",\
"is_tentative":false}
"""

_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=_SYSTEM),
    HumanMessagePromptTemplate.from_template("{email_text}"),
])

_chain: Runnable | None = None


def get_action_chain() -> Runnable:
    global _chain
    if _chain is None:
        llm = get_groq_llm(temperature=0.0, max_tokens=400)
        _chain = (_prompt | llm | JsonOutputParser()).with_retry(
            stop_after_attempt=3,
        )
    return _chain
