"""
Extended flowchart benchmark — backend/tests/test_flowchart_extended.py

Coverage
--------
  PP01-PP14  Project-plan / process emails — must return has_flowchart=True
  PP15       Long plan (12 numbered steps) — must compress to ≤ 8 nodes
  NP01-NP10  Non-plan emails — must return has_flowchart=False

Pass criteria
-------------
  PP: >= 13/15  (87%)
  NP: >= 9/10   (90%)
  Overall: >= 22/25  (88%)

Run: python backend/tests/test_flowchart_extended.py
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, "backend")

_env = Path(__file__).parent.parent / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

from app.flowchart_agent import detect_flowchart

VALID_NODE_TYPES = {"start", "end", "step", "decision"}

# ── Emails ────────────────────────────────────────────────────────────────────

PLAN_EMAILS = [
    {
        "id": "PP01",
        "subject": "Q4 product launch — 5-phase plan",
        "body": (
            "Team, here is the approved Q4 launch plan:\n\n"
            "Phase 1 (Oct 1-7): Finalize requirements and freeze the feature scope.\n"
            "Phase 2 (Oct 8-21): Engineering build and unit tests.\n"
            "Phase 3 (Oct 22-28): QA regression and bug fixes.\n"
            "Phase 4 (Oct 29): Staged rollout to 10% of users.\n"
            "Phase 5 (Nov 1): Full production release and marketing go-live."
        ),
        "expect": True,
        "max_nodes": 8,
    },
    {
        "id": "PP02",
        "subject": "Marketing campaign — 4-stage rollout",
        "body": (
            "Campaign launch plan for the spring promotion:\n\n"
            "Stage 1 — Awareness (Weeks 1-2): Run paid social ads and influencer posts.\n"
            "Stage 2 — Consideration (Weeks 3-4): Launch email drip campaign and retargeting.\n"
            "Stage 3 — Conversion (Week 5): Activate promotional discount codes.\n"
            "Stage 4 — Retention (Week 6+): Post-purchase follow-up emails and loyalty rewards."
        ),
        "expect": True,
        "max_nodes": 8,
    },
    {
        "id": "PP03",
        "subject": "Hiring pipeline — engineering roles",
        "body": (
            "For all engineering hires, the pipeline is as follows:\n\n"
            "1. Recruiter phone screen (30 min).\n"
            "2. Take-home technical exercise — 48-hour window.\n"
            "   - Pass: proceed to panel interviews.\n"
            "   - Fail: send decline email.\n"
            "3. Panel interviews: system design (1 hr) + coding (1 hr) + culture fit (30 min).\n"
            "4. Hiring committee review and final decision.\n"
            "5. Offer extended and background check initiated."
        ),
        "expect": True,
        "max_nodes": 8,
    },
    {
        "id": "PP04",
        "subject": "Annual security audit process",
        "body": (
            "The annual security audit follows these steps:\n\n"
            "Step 1: Scope definition — identify systems and assets in scope.\n"
            "Step 2: Vulnerability scanning using automated tools.\n"
            "Step 3: Penetration testing by the external firm.\n"
            "Step 4: Review findings and classify by severity (Critical / High / Medium / Low).\n"
            "Step 5: Remediation — teams address findings within agreed SLAs.\n"
            "Step 6: Re-test to verify fixes. Issue compliance certificate."
        ),
        "expect": True,
        "max_nodes": 8,
    },
    {
        "id": "PP05",
        "subject": "Annual conference — planning timeline",
        "body": (
            "Here is the planning timeline for the annual summit:\n\n"
            "6 months out: Venue selection and contract signing.\n"
            "4 months out: Speaker invitations and agenda draft.\n"
            "3 months out: Ticket sales open; sponsor outreach begins.\n"
            "2 months out: Catering, A/V, and logistics confirmed.\n"
            "2 weeks out: Attendee confirmation emails and badge printing.\n"
            "Event day: On-site check-in, live sessions, networking dinner.\n"
            "Post-event: Attendee survey and debrief report."
        ),
        "expect": True,
        "max_nodes": 8,
    },
    {
        "id": "PP06",
        "subject": "B2B sales process — 6 stages",
        "body": (
            "Our standard B2B sales process:\n\n"
            "1. Lead qualification — confirm budget, authority, need, timeline (BANT).\n"
            "2. Discovery call — understand pain points and desired outcomes.\n"
            "3. Demo and proposal — tailored demo followed by a written proposal.\n"
            "4. Negotiation — pricing, terms, and legal review.\n"
            "5. Contract signing — DocuSign.\n"
            "6. Handover to Customer Success for onboarding."
        ),
        "expect": True,
        "max_nodes": 8,
    },
    {
        "id": "PP07",
        "subject": "Blog post production workflow",
        "body": (
            "All blog posts must go through this workflow before publishing:\n\n"
            "1. Topic approved by content lead.\n"
            "2. Writer drafts the post and submits for review.\n"
            "3. Editor reviews:\n"
            "   - Approved: moves to SEO review.\n"
            "   - Rejected: returned to writer with feedback.\n"
            "4. SEO team adds meta tags and optimises headings.\n"
            "5. Legal approves any claims or statistics.\n"
            "6. Publish and distribute across social channels."
        ),
        "expect": True,
        "max_nodes": 8,
    },
    {
        "id": "PP08",
        "subject": "Capital expenditure approval workflow",
        "body": (
            "All CapEx requests follow this approval chain:\n\n"
            "1. Department manager submits request in ERP with business justification.\n"
            "2. Finance reviews for budget availability.\n"
            "   - Approved: escalated based on amount.\n"
            "   - Rejected: returned with comments.\n"
            "3. Requests < $25k: VP approval only.\n"
            "4. Requests $25k–$250k: VP + CFO approval.\n"
            "5. Requests > $250k: Board approval required.\n"
            "6. Upon approval, PO is issued."
        ),
        "expect": True,
        "max_nodes": 8,
    },
    {
        "id": "PP09",
        "subject": "Customer onboarding journey",
        "body": (
            "New customers go through a 6-week structured onboarding:\n\n"
            "Week 1 — Kickoff: intro call, account setup, SSO configuration.\n"
            "Week 2 — Training: platform walkthrough and admin training.\n"
            "Week 3 — Data migration: import historical data and validate.\n"
            "Week 4 — Pilot: select team runs first live workflow.\n"
            "Week 5 — Rollout: full team enablement sessions.\n"
            "Week 6 — Review: success metrics review and 90-day plan."
        ),
        "expect": True,
        "max_nodes": 8,
    },
    {
        "id": "PP10",
        "subject": "Data centre migration — dual-workstream plan",
        "body": (
            "Migration will run as two parallel workstreams converging at cut-over:\n\n"
            "Workstream A — Infrastructure: provision new cloud VPCs, configure networking "
            "and load balancers, replicate databases to new region using DMS.\n\n"
            "Workstream B — Applications: containerise all services, update environment "
            "configs, run integration tests against the new endpoints.\n\n"
            "Both workstreams must pass their acceptance criteria before cut-over. "
            "Cut-over: update DNS, retire old data centre, 30-day parallel-run monitoring."
        ),
        "expect": True,
        "max_nodes": 8,
    },
    {
        "id": "PP11",
        "subject": "Quarterly business review preparation",
        "body": (
            "QBR preparation process (starts 3 weeks before the review date):\n\n"
            "Week -3: Each team lead collects KPIs and writes their section.\n"
            "Week -2: Finance consolidates P&L and pipeline data.\n"
            "Week -1: Draft deck circulated for exec review and edits.\n"
            "Day -2: Final deck locked. Logistics confirmed (room, dial-in).\n"
            "QBR day: Presentation, Q&A, decision log captured.\n"
            "Week +1: Action items distributed and tracked in project tracker."
        ),
        "expect": True,
        "max_nodes": 8,
    },
    {
        "id": "PP12",
        "subject": "P1 incident response procedure",
        "body": (
            "When a P1 incident is declared:\n\n"
            "1. On-call engineer opens a war-room bridge and pages the engineering manager.\n"
            "2. Within 15 minutes: post initial status update in #incidents.\n"
            "3. Root cause investigation:\n"
            "   - Root cause identified: implement hotfix, verify in staging, deploy.\n"
            "   - Root cause unknown after 1 hour: page VP Engineering and external support.\n"
            "4. Resolution: verify metrics return to normal baseline.\n"
            "5. Post-incident: publish blameless postmortem within 48 hours."
        ),
        "expect": True,
        "max_nodes": 8,
    },
    {
        "id": "PP13",
        "subject": "New office setup — project plan",
        "body": (
            "Project plan for the London office opening:\n\n"
            "Month 1: Sign lease, engage fit-out contractor, order furniture.\n"
            "Month 2: Electrical, networking, and HVAC installation.\n"
            "Month 3: Furniture delivery and IT equipment setup.\n"
            "Month 4: Staff relocations and day-one welcome event.\n"
            "Month 5: Post-move review and snag list resolution."
        ),
        "expect": True,
        "max_nodes": 8,
    },
    {
        "id": "PP14",
        "subject": "Software release checklist — v3.0",
        "body": (
            "Before we ship v3.0, complete each gate in order:\n\n"
            "Gate 1: All P0 and P1 bugs resolved and verified by QA.\n"
            "Gate 2: Performance benchmarks within 5% of baseline.\n"
            "Gate 3: Security scan clean — no High or Critical findings.\n"
            "Gate 4: Release notes and changelog reviewed by Product.\n"
            "Gate 5: Staging smoke test passing. Go/No-Go sign-off from engineering lead.\n"
            "Gate 6: Deploy to production. Monitor error rates for 2 hours.\n"
            "Gate 7: Customer comms sent and support team briefed."
        ),
        "expect": True,
        "max_nodes": 8,
    },
    {
        "id": "PP15",
        "subject": "12-step compliance audit process",
        "body": (
            "Here are the 12 steps for the annual compliance audit:\n\n"
            "1. Notify all department heads of the audit schedule.\n"
            "2. Collect current policy and procedure documents.\n"
            "3. Review documents against the latest regulatory requirements.\n"
            "4. Conduct employee interviews to assess awareness.\n"
            "5. Identify gaps and areas of non-compliance.\n"
            "6. Classify gaps by risk level (Critical / High / Medium / Low).\n"
            "7. Assign remediation owners for each gap.\n"
            "8. Implement corrective actions within agreed timelines.\n"
            "9. Document evidence of changes made.\n"
            "10. Internal review team validates the evidence.\n"
            "11. External auditor conducts independent review.\n"
            "12. Obtain compliance certification if no major findings remain."
        ),
        "expect": True,
        "max_nodes": 8,  # must compress 12 steps to ≤ 8 nodes
    },
]

NON_PLAN_EMAILS = [
    {
        "id": "NP01",
        "subject": "Meeting request — Thursday 2pm",
        "body": (
            "Hi Alex, are you free on Thursday at 2pm to discuss the Q3 budget? "
            "I'd like to go over the variance report and align on headcount. "
            "Let me know and I can send a calendar invite. Thanks!"
        ),
        "expect": False,
    },
    {
        "id": "NP02",
        "subject": "Offer letter — Software Engineer",
        "body": (
            "Dear Jordan,\n\n"
            "We are delighted to offer you the position of Software Engineer at Acme Corp, "
            "starting Monday, August 4. Your annual salary will be $145,000. "
            "Please sign and return the enclosed offer letter by July 25. "
            "We look forward to having you on the team!"
        ),
        "expect": False,
    },
    {
        "id": "NP03",
        "subject": "Team lunch — Friday noon",
        "body": (
            "Hey everyone, joining us for lunch this Friday at noon? "
            "We're thinking the Thai place on 5th. "
            "Reply here so I can book the right table size. Cheers!"
        ),
        "expect": False,
    },
    {
        "id": "NP04",
        "subject": "Project status — Week 31",
        "body": (
            "Quick status for Week 31:\n\n"
            "Completed: login redesign shipped, rate-limiting deployed.\n"
            "In progress: payment gateway integration (70% done).\n"
            "Blocked: staging deploy — DevOps investigating the CI runner issue.\n"
            "On track for the August 15 release."
        ),
        "expect": False,
    },
    {
        "id": "NP05",
        "subject": "Complaint — incorrect invoice",
        "body": (
            "I received invoice #INV-4421 for $4,800 but our contract specifies $3,900 "
            "for the standard tier. This is the second billing error this quarter. "
            "Please issue a corrected invoice and a credit note for the difference immediately."
        ),
        "expect": False,
    },
    {
        "id": "NP06",
        "subject": "Out of office — back August 12",
        "body": (
            "Thank you for your email. I am out of the office from August 5 to August 11 "
            "with limited access to email. I will respond upon my return on August 12. "
            "For urgent matters, please contact my colleague Sarah at sarah@company.com."
        ),
        "expect": False,
    },
    {
        "id": "NP07",
        "subject": "August product newsletter",
        "body": (
            "Hi there! Here is what is new in August:\n\n"
            "New: Dark mode is now available in Settings > Appearance.\n"
            "Improved: Bulk export is 3× faster.\n"
            "Coming soon: Custom dashboards, launching September 1.\n\n"
            "Read our blog for the full release notes. Happy building!"
        ),
        "expect": False,
    },
    {
        "id": "NP08",
        "subject": "FAQ — how do I reset my password?",
        "body": (
            "Hi, to reset your password go to the login page and click "
            "'Forgot password'. Enter your email and you will receive a reset link "
            "within 5 minutes. The link expires after 24 hours. "
            "If you do not receive the email, check your spam folder. "
            "Let me know if you need further help."
        ),
        "expect": False,
    },
    {
        "id": "NP09",
        "subject": "Two quick things",
        "body": (
            "Hi Sam, just two things:\n"
            "1. Can you review the PR I opened this morning?\n"
            "2. The client called — they want to push the demo to next week.\n"
            "Let me know on both. Thanks."
        ),
        "expect": False,
    },
    {
        "id": "NP10",
        "subject": "Congratulations on the promotion!",
        "body": (
            "Hi Maria, I just heard the great news — congratulations on your promotion "
            "to Senior Director! You have worked incredibly hard and thoroughly deserve it. "
            "Looking forward to continuing to work with you in your new role. "
            "Let's celebrate soon!"
        ),
        "expect": False,
    },
]

SEP = "-" * 70


def _check(em: dict, result: dict) -> list[str]:
    issues: list[str] = []
    got = result.get("has_flowchart", False)
    exp = em["expect"]

    if got != exp:
        issues.append(f"has_flowchart expected={exp} got={got}")
        return issues

    if not exp:
        return issues

    nodes = result.get("nodes", [])
    edges = result.get("edges", [])
    max_n = em.get("max_nodes", 8)

    if not (3 <= len(nodes) <= max_n):
        issues.append(f"node count {len(nodes)} outside [3, {max_n}]")

    bad_types = [n["type"] for n in nodes if n.get("type") not in VALID_NODE_TYPES]
    if bad_types:
        issues.append(f"invalid node types: {bad_types}")

    starts = [n for n in nodes if n.get("type") == "start"]
    if len(starts) != 1:
        issues.append(f"expected 1 start node, got {len(starts)}")

    valid_ids = {n["id"] for n in nodes}
    bad_edges = [
        (e.get("source"), e.get("target"))
        for e in edges
        if e.get("source") not in valid_ids or e.get("target") not in valid_ids
    ]
    if bad_edges:
        issues.append(f"edges reference unknown ids: {bad_edges}")

    mermaid = result.get("mermaid", "")
    if not mermaid.startswith("flowchart TD"):
        issues.append("mermaid missing or wrong header")

    return issues


async def run() -> tuple[int, int, int]:
    all_emails = PLAN_EMAILS + NON_PLAN_EMAILS
    pp_pass = pp_fail = np_pass = np_fail = 0

    print(f"\nFlowchart extended benchmark — {len(all_emails)} emails\n")

    print("── Project-plan emails (PP) ──")
    print(SEP)
    for em in PLAN_EMAILS:
        result = await detect_flowchart(em["subject"], em["body"])
        await asyncio.sleep(0.4)
        issues = _check(em, result)
        ok = not issues

        if ok:
            pp_pass += 1
        else:
            pp_fail += 1

        fc    = result.get("has_flowchart", False)
        ncount = len(result.get("nodes", []))
        ftype  = result.get("flowchart_type") or "-"
        status = "PASS" if ok else "FAIL"
        print(f"  {em['id']}  {status}  has_flowchart={fc}  type={ftype}  nodes={ncount}")
        for issue in issues:
            print(f"    x {issue}")

    pp_total = len(PLAN_EMAILS)
    print(SEP)
    pp_pct = pp_pass / pp_total * 100
    pp_result = "PASS" if pp_pass >= 13 else "FAIL"
    print(f"PP: {pp_pass}/{pp_total} = {pp_pct:.0f}%  (target >= 13/15)  [{pp_result}]")

    print("\n── Non-plan emails (NP) ──")
    print(SEP)
    for em in NON_PLAN_EMAILS:
        result = await detect_flowchart(em["subject"], em["body"])
        await asyncio.sleep(0.4)
        issues = _check(em, result)
        ok = not issues

        if ok:
            np_pass += 1
        else:
            np_fail += 1

        fc    = result.get("has_flowchart", False)
        status = "PASS" if ok else "FAIL"
        print(f"  {em['id']}  {status}  has_flowchart={fc}")
        for issue in issues:
            print(f"    x {issue}")

    np_total = len(NON_PLAN_EMAILS)
    print(SEP)
    np_pct = np_pass / np_total * 100
    np_result = "PASS" if np_pass >= 9 else "FAIL"
    print(f"NP: {np_pass}/{np_total} = {np_pct:.0f}%  (target >= 9/10)   [{np_result}]")

    total_pass = pp_pass + np_pass
    total      = pp_total + np_total
    overall_pct = total_pass / total * 100
    overall_ok  = pp_pass >= 13 and np_pass >= 9

    print(f"\nOverall: {total_pass}/{total} = {overall_pct:.0f}%  (target >= 22/25)")
    print("BENCHMARK PASSED" if overall_ok else "BENCHMARK FAILED")

    return pp_fail, np_fail, 0 if overall_ok else 1


if __name__ == "__main__":
    pp_fail, np_fail, exit_code = asyncio.run(run())
    sys.exit(exit_code)
