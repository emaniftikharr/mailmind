"""
LCEL chain: task extraction from email text.

Identifies action items directed at the recipient ("me"), returns a structured
list. Uses SystemMessage so JSON examples don't conflict with LangChain's
template variable parser.
"""
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.runnables import Runnable

from app.chains.base import get_groq_llm

MAX_INPUT_CHARS = 3_000

_PRIORITIES = ("urgent", "high", "normal", "low")

_SYSTEM = """\
You are a task-extraction assistant. Given an email, identify action items that \
the RECIPIENT (the person reading this email) is being asked to do. \
Respond with valid JSON only — no prose, no markdown fences.

OUTPUT SCHEMA
{
  "tasks": [
    {
      "title":        <string — concise imperative phrase, ≤ 8 words>,
      "description":  <string — one sentence with context>,
      "assignee":     <"me" | "them" | "other">,
      "due_date_str": <string — exact phrasing from email, or "">,
      "priority":     <"urgent" | "high" | "normal" | "low">
    }
  ]
}

RULES
- assignee "me"    = the recipient must do this (requests, imperatives, action items)
- assignee "them"  = the sender said they will do this ("I'll send you…", "I will prepare…")
- assignee "other" = unclear or a third party
- Only include assignee="them" / "other" tasks when they are significant follow-up items
  the recipient should track (e.g., "I'll deliver the contract by Monday").
- Omit purely informational sentences that require no action from anyone.
- priority "urgent"  = same-day deadline or "ASAP" / "immediately"
- priority "high"    = 1–2 day window or explicitly "important" / "urgent"
- priority "normal"  = within a week or no stated time pressure
- priority "low"     = "whenever you get a chance", "no rush", "when possible"
- Keep title as an imperative: "Send Q3 report", "Review contract", "Schedule call".

EXAMPLES

Email: "Hi Alex, could you please send me the Q3 sales report by Friday? \
I need it for the board presentation."
Output: {"tasks":[{"title":"Send Q3 sales report","description":"Recipient was asked to \
send the Q3 sales report for a board presentation","assignee":"me",\
"due_date_str":"by Friday","priority":"high"}]}

Email: "Hi team, two quick things: 1) Can you review the attached contract and flag \
any issues? 2) Please update the project timeline in Jira by Monday."
Output: {"tasks":[{"title":"Review attached contract","description":"Review the contract \
document and flag any issues","assignee":"me","due_date_str":"","priority":"normal"},\
{"title":"Update project timeline in Jira","description":"Update the Jira project \
timeline","assignee":"me","due_date_str":"by Monday","priority":"high"}]}

Email: "Just a heads-up — the server migration completed successfully last night. \
No action needed. Logs are attached for reference."
Output: {"tasks":[]}

Email: "I'll prepare the slides and send them to you by tomorrow morning. \
Let me know if you want any changes."
Output: {"tasks":[{"title":"Confirm slide changes","description":"Sender is preparing \
slides and will send by tomorrow — reply if changes are needed","assignee":"them",\
"due_date_str":"by tomorrow","priority":"normal"}]}

Email: "Following our call: Action item for you: schedule a follow-up demo with \
the client team by next week. Action item for me: prepare the pricing deck."
Output: {"tasks":[{"title":"Schedule follow-up demo with client","description":\
"Action item from call: schedule a follow-up demo with the client team",\
"assignee":"me","due_date_str":"by next week","priority":"normal"},\
{"title":"Prepare pricing deck","description":"Sender will prepare the pricing deck",\
"assignee":"them","due_date_str":"","priority":"normal"}]}
"""

_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=_SYSTEM),
    HumanMessagePromptTemplate.from_template("{email_text}"),
])

_chain: Runnable | None = None


def get_task_chain() -> Runnable:
    global _chain
    if _chain is None:
        llm = get_groq_llm(temperature=0.0, max_tokens=512)
        _chain = (_prompt | llm | JsonOutputParser()).with_retry(
            stop_after_attempt=3,
        )
    return _chain
