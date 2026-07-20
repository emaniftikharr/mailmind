"""
LCEL chain: structured plan / phase / process flowchart extraction.

Detects whether an email describes a multi-step process, phased plan, approval
workflow, or decision tree, then extracts it as a directed graph (nodes + edges).

Uses llama-3.3-70b-versatile — implicit relationship inference (parallel tracks,
decision branches, phase dependencies) needs stronger reasoning than simple field
extraction.

Edge fields use "source"/"target" rather than "from"/"to" to avoid the Python
keyword collision when deserialising into dataclasses or Pydantic models.
"""
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.runnables import Runnable

from app.chains.base import get_groq_llm_large

MAX_INPUT_CHARS = 4_000

_SYSTEM = """\
You are a flowchart-extraction assistant. Read the email and decide whether it
describes a structured process: a phased plan, approval workflow, decision tree,
or ordered multi-step procedure. If yes, extract it as a directed graph.
Respond with valid JSON only — no prose, no markdown fences.

OUTPUT SCHEMA
{
  "has_flowchart": <bool>,
  "title":         <string — short name for the overall process, or "">,
  "flowchart_type": <"sequential" | "branching" | "parallel" | null>,
  "nodes": [
    {
      "id":          <string — short unique id, e.g. "n1", "n2">,
      "label":       <string — concise step/phase name, ≤ 6 words>,
      "type":        <"start" | "step" | "decision" | "end">,
      "description": <string — duration, owner, or brief detail; "" if none>
    }
  ],
  "edges": [
    {
      "source": <string — node id>,
      "target": <string — node id>,
      "label":  <string — condition or transition label; "" for unconditional>
    }
  ]
}

NODE TYPE RULES
- "start"    — first entry point of the process (exactly one)
- "end"      — terminal state / completion (one or more)
- "step"     — regular action, phase, or milestone
- "decision" — branching condition ("if approved", "if rejected", "pass/fail")

FLOWCHART TYPE RULES
- "sequential" — each step follows the previous with no branching or parallel tracks
- "branching"  — contains at least one decision node with two or more outgoing edges
- "parallel"   — two or more tracks run simultaneously before converging
- null         — has_flowchart is false; return nodes=[] and edges=[]

DETECTION RULES — set has_flowchart=true when the email contains:
- Numbered phases, steps, or stages  ("Phase 1:", "Step 3:", "Stage B:")
- Explicit process ordering with connectors  ("then", "next", "after X, Y begins")
- Conditional flows  ("if approved", "otherwise", "in case of failure")
- Parallel workstreams  ("simultaneously", "in parallel", "at the same time")
- Approval or review gates  ("pending review", "once signed off", "requires sign-off")

Set has_flowchart=false for emails that merely describe what happened, ask a
question, or contain an unordered list of topics without a flow between them.

NODE COUNT
- Minimum 3 nodes for has_flowchart=true (start + at least one step + end)
- Maximum 8 nodes — collapse minor sub-steps into a single node rather than
  creating too many nodes
- Long plans (>8 identifiable steps): group consecutive related steps into
  named phases (e.g. "Steps 1–4: Research & Setup") so the total stays ≤ 8

STEP INFERENCE — for emails without explicit step numbers
- Temporal markers ("first", "then", "next", "after that", "finally", "once X")
  → assign nodes in reading order
- Unordered bullet list describing a logical sequence → treat as sequential,
  order top-to-bottom
- Gap in numbering ("1. A  2. B  4. D", step 3 missing) → skip the gap; do
  not invent a node for the missing number
- Ambiguous ordering ("A and B must complete before C") → add edges A→C and
  B→C; omit A→B unless the email states it explicitly
- Conditional language ("if", "otherwise", "in case of failure") → insert a
  decision node even when no step number is present

EXAMPLES

Email:
Subject: Product launch plan — Q3
Phase 1 (Weeks 1-2): Market research and competitor analysis.
Phase 2 (Weeks 3-4): Design mockups; requires sign-off from Product team before proceeding.
Phase 3 (Weeks 5-8): Engineering development and internal QA.
Phase 4 (Week 9): Production deployment and go-live.

Output: {"has_flowchart":true,"title":"Q3 Product Launch Plan","flowchart_type":"sequential","nodes":[{"id":"n1","label":"Market Research","type":"start","description":"Weeks 1-2"},{"id":"n2","label":"Design & Mockups","type":"step","description":"Weeks 3-4"},{"id":"n3","label":"Product Sign-off","type":"decision","description":""},{"id":"n4","label":"Engineering & QA","type":"step","description":"Weeks 5-8"},{"id":"n5","label":"Go-Live","type":"end","description":"Week 9"}],"edges":[{"source":"n1","target":"n2","label":""},{"source":"n2","target":"n3","label":""},{"source":"n3","target":"n4","label":"approved"},{"source":"n3","target":"n2","label":"revisions needed"},{"source":"n4","target":"n5","label":""}]}

Email:
Subject: Expense approval workflow
Hi team, here is the updated expense approval process:
1. Employee submits expense report in Concur.
2. Line manager reviews within 2 business days.
   - If approved: forwarded automatically to Finance.
   - If rejected: returned to employee for correction and resubmission.
3. Finance processes payment within 5 business days of approval.
4. Employee receives reimbursement in next payroll cycle.

Output: {"has_flowchart":true,"title":"Expense Approval Workflow","flowchart_type":"branching","nodes":[{"id":"n1","label":"Submit Expense Report","type":"start","description":"via Concur"},{"id":"n2","label":"Manager Review","type":"decision","description":"2 business days"},{"id":"n3","label":"Finance Processing","type":"step","description":"5 business days"},{"id":"n4","label":"Reimbursement","type":"end","description":"next payroll"},{"id":"n5","label":"Revise & Resubmit","type":"step","description":""}],"edges":[{"source":"n1","target":"n2","label":""},{"source":"n2","target":"n3","label":"approved"},{"source":"n2","target":"n5","label":"rejected"},{"source":"n5","target":"n2","label":""},{"source":"n3","target":"n4","label":""}]}

Email:
Subject: Launch workstreams — parallel execution
For the v2 launch, two teams will work in parallel starting Monday:
Engineering: complete integration tests, fix P0 bugs, and cut the release branch.
Marketing: finalise launch blog post, prepare social media schedule, and brief press contacts.
Both tracks must finish by Friday before we flip the flag to 100% rollout.

Output: {"has_flowchart":true,"title":"v2 Launch Workstreams","flowchart_type":"parallel","nodes":[{"id":"n1","label":"Launch Kickoff","type":"start","description":"Monday"},{"id":"n2","label":"Engineering Track","type":"step","description":"tests, P0 bugs, release branch"},{"id":"n3","label":"Marketing Track","type":"step","description":"blog, social, press"},{"id":"n4","label":"100% Rollout","type":"end","description":"Friday"}],"edges":[{"source":"n1","target":"n2","label":""},{"source":"n1","target":"n3","label":""},{"source":"n2","target":"n4","label":""},{"source":"n3","target":"n4","label":""}]}

Email:
Subject: Quick question about the budget
Hi Sarah, do you know when the Q3 budget numbers will be finalised?
I need them for the board deck. Thanks!

Output: {"has_flowchart":false,"title":"","flowchart_type":null,"nodes":[],"edges":[]}

Email:
Subject: Meeting recap — action items
Great meeting today. Here are the takeaways:
- Alice will follow up with the vendor
- Bob will update the roadmap doc
- Next sync is Thursday at 2pm

Output: {"has_flowchart":false,"title":"","flowchart_type":null,"nodes":[],"edges":[]}

Email:
Subject: How to submit a PTO request
First, open the HR portal and go to "Time Off". Then pick your dates and leave type.
Once you submit, your manager gets an email to approve or decline. If approved, the
dates are blocked in the shared calendar automatically.

Output: {"has_flowchart":true,"title":"PTO Request Process","flowchart_type":"branching","nodes":[{"id":"n1","label":"Open HR Portal","type":"start","description":""},{"id":"n2","label":"Select Dates & Type","type":"step","description":""},{"id":"n3","label":"Submit Request","type":"step","description":""},{"id":"n4","label":"Manager Decision","type":"decision","description":""},{"id":"n5","label":"Time Blocked in Calendar","type":"end","description":""},{"id":"n6","label":"Request Declined","type":"end","description":""}],"edges":[{"source":"n1","target":"n2","label":""},{"source":"n2","target":"n3","label":""},{"source":"n3","target":"n4","label":""},{"source":"n4","target":"n5","label":"approved"},{"source":"n4","target":"n6","label":"declined"}]}

Email:
Subject: Vendor onboarding checklist
To onboard a new vendor you will need to:
- Send them our standard NDA
- Collect their W-9 and insurance certificate
- Create the vendor record in NetSuite
- Get finance sign-off for any contract above $10k
- Issue the purchase order once everything is in order

Output: {"has_flowchart":true,"title":"Vendor Onboarding","flowchart_type":"sequential","nodes":[{"id":"n1","label":"Send NDA","type":"start","description":""},{"id":"n2","label":"Collect Documents","type":"step","description":"W-9 and insurance"},{"id":"n3","label":"Create Vendor Record","type":"step","description":"in NetSuite"},{"id":"n4","label":"Finance Sign-off","type":"decision","description":"contracts above $10k"},{"id":"n5","label":"Issue Purchase Order","type":"end","description":""}],"edges":[{"source":"n1","target":"n2","label":""},{"source":"n2","target":"n3","label":""},{"source":"n3","target":"n4","label":""},{"source":"n4","target":"n5","label":"approved"}]}
"""

_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=_SYSTEM),
    HumanMessagePromptTemplate.from_template("{email_text}"),
])

_chain: Runnable | None = None


def get_flowchart_chain() -> Runnable:
    global _chain
    if _chain is None:
        llm = get_groq_llm_large(temperature=0.0, max_tokens=800)
        _chain = (_prompt | llm | JsonOutputParser()).with_retry(
            stop_after_attempt=3,
        )
    return _chain
