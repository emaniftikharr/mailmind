"""
Flowchart extraction benchmark — backend/tests/test_flowchart.py

Coverage
--------
  SEQ01-SEQ04  Sequential phased plans (project plan, onboarding, deployment, rollout)
  BRN01-BRN03  Branching / approval flows (expense, code review, incident escalation)
  PAR01-PAR02  Parallel workstreams (product launch, data migration)
  NEG01-NEG06  Negative cases — must return has_flowchart=False:
               quick question, meeting recap, status update, complaint,
               newsletter, simple task request

Pass criteria per email
-----------------------
  has_flowchart matches expected
  When has_flowchart=True:
    node count >= 3 and <= 10
    all node types valid (start/end/step/decision)
    all edges reference valid node ids
    exactly one "start" node
    mermaid field is non-empty and starts with "flowchart TD"

Overall: >= 13/15 (87%)

Run: python backend/tests/test_flowchart.py
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, "backend")

_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

from app.flowchart_agent import detect_flowchart

VALID_NODE_TYPES = {"start", "end", "step", "decision"}

EMAILS = [
    # ── Sequential ─────────────────────────────────────────────────────────────
    {
        "id": "SEQ01",
        "subject": "Q3 product launch — phased plan",
        "body": (
            "Hi team, here is the approved Q3 product launch plan:\n\n"
            "Phase 1 (Weeks 1-2): Market research, competitor analysis, and user interviews.\n"
            "Phase 2 (Weeks 3-4): Design mockups and prototype; requires Product sign-off before proceeding.\n"
            "Phase 3 (Weeks 5-8): Engineering development and internal QA testing.\n"
            "Phase 4 (Week 9): Staged production deployment and monitoring.\n"
            "Phase 5 (Week 10): Full public go-live and marketing push."
        ),
        "expect": True,
        "expect_type": "sequential",
    },
    {
        "id": "SEQ02",
        "subject": "New employee onboarding checklist",
        "body": (
            "Welcome to the team! Here is your onboarding journey:\n\n"
            "Step 1 (Day 1): Complete I-9 and tax forms in Workday. Collect laptop from IT.\n"
            "Step 2 (Days 1-3): Complete security and compliance training modules.\n"
            "Step 3 (Week 1): Shadow your team lead and attend all standups.\n"
            "Step 4 (Week 2): Complete your starter task and submit a PR for review.\n"
            "Step 5 (Day 30): First 1:1 review with your manager. Set 90-day goals."
        ),
        "expect": True,
        "expect_type": "sequential",
    },
    {
        "id": "SEQ03",
        "subject": "Database migration runbook — Saturday night",
        "body": (
            "Migration runbook for the Saturday 02:00 UTC window:\n\n"
            "1. Take a full database snapshot and verify it (10 min).\n"
            "2. Enable maintenance mode — all API requests return 503.\n"
            "3. Run migration scripts in order: 001_schema.sql, 002_indexes.sql, 003_data.sql.\n"
            "4. Run smoke tests against the new schema.\n"
            "5. If smoke tests pass, disable maintenance mode and monitor dashboards.\n"
            "6. Confirm rollback checkpoint is clean before closing the window."
        ),
        "expect": True,
        "expect_type": None,  # accept any type — could be sequential or branching
    },
    {
        "id": "SEQ04",
        "subject": "Feature flag rollout strategy",
        "body": (
            "We will roll out the new payments UI using the following staged approach:\n\n"
            "Stage 1: Internal employees only (0.5% of traffic) — 48 hours.\n"
            "Stage 2: Beta users (5%) — monitor error rates and latency for 72 hours.\n"
            "Stage 3: Broad rollout (50%) — watch conversion metrics for 1 week.\n"
            "Stage 4: 100% rollout — full public release.\n\n"
            "We will pause and rollback at any stage if error rate exceeds 0.5%."
        ),
        "expect": True,
        "expect_type": "sequential",
    },
    # ── Branching ──────────────────────────────────────────────────────────────
    {
        "id": "BRN01",
        "subject": "Updated expense approval process",
        "body": (
            "Effective Monday, the expense approval process is as follows:\n\n"
            "1. Employee submits expense report in Concur.\n"
            "2. Line manager reviews within 2 business days.\n"
            "   - Approved: automatically forwarded to Finance for payment.\n"
            "   - Rejected: returned to employee with comments for correction and resubmission.\n"
            "3. Finance processes payment within 5 business days.\n"
            "4. Reimbursement appears in the next payroll cycle."
        ),
        "expect": True,
        "expect_type": "branching",
    },
    {
        "id": "BRN02",
        "subject": "Code review and merge policy",
        "body": (
            "From next sprint, all PRs must follow this process:\n\n"
            "1. Developer opens PR against main.\n"
            "2. CI pipeline runs automated tests.\n"
            "   - Tests pass: PR moves to peer review.\n"
            "   - Tests fail: PR blocked; developer fixes and re-pushes.\n"
            "3. Two reviewers must approve. If changes are requested, developer addresses them "
            "and re-requests review.\n"
            "4. Once two approvals are in, tech lead merges to main."
        ),
        "expect": True,
        "expect_type": "branching",
    },
    {
        "id": "BRN03",
        "subject": "Incident escalation policy",
        "body": (
            "When a production incident is detected:\n\n"
            "1. On-call engineer investigates and classifies severity.\n"
            "   - P1 (full outage): immediately page the engineering manager and VP Engineering.\n"
            "   - P2 (partial degradation): notify team lead; resolve within 4 hours.\n"
            "   - P3 (minor issue): log in Jira and fix in next sprint.\n"
            "2. For P1 incidents: open a war-room bridge, post status in #incidents, and update "
            "the status page every 30 minutes.\n"
            "3. Post-incident: write a blameless postmortem within 48 hours."
        ),
        "expect": True,
        "expect_type": "branching",
    },
    # ── Parallel ───────────────────────────────────────────────────────────────
    {
        "id": "PAR01",
        "subject": "v2 launch — parallel execution plan",
        "body": (
            "Starting Monday, two teams will execute in parallel:\n\n"
            "Engineering track: finalize integration tests, fix all P0 bugs, cut the release "
            "branch, and deploy to staging.\n\n"
            "Marketing track: publish launch blog post, schedule social media posts, and brief "
            "press contacts under NDA.\n\n"
            "Both tracks must complete by Friday noon before we flip the feature flag to 100%."
        ),
        "expect": True,
        "expect_type": "parallel",
    },
    {
        "id": "PAR02",
        "subject": "Data centre migration — dual-track plan",
        "body": (
            "The migration will run as two simultaneous workstreams:\n\n"
            "Workstream A (Infrastructure): provision new cloud VPCs, configure networking, "
            "and replicate databases to the new region.\n\n"
            "Workstream B (Application): containerise all services, update config for the new "
            "endpoints, and run smoke tests on staging.\n\n"
            "Both workstreams converge at the cutover window on Saturday at 02:00 UTC, where "
            "we switch DNS and decommission the old data centre."
        ),
        "expect": True,
        "expect_type": "parallel",
    },
    # ── Negative cases — must return has_flowchart=False ──────────────────────
    {
        "id": "NEG01",
        "subject": "Quick question about the budget",
        "body": "Hi Sarah, do you know when the Q3 budget numbers will be finalised? I need them for the board deck. Thanks!",
        "expect": False,
        "expect_type": None,
    },
    {
        "id": "NEG02",
        "subject": "Meeting recap — Tuesday standup",
        "body": (
            "Great standup today! Recap:\n"
            "- Alice is working on the auth refactor, ETA Thursday\n"
            "- Bob fixed the export bug, PR open\n"
            "- Charlie is OOO Wednesday\n"
            "Next standup: Wednesday 9 AM"
        ),
        "expect": False,
        "expect_type": None,
    },
    {
        "id": "NEG03",
        "subject": "Sprint status update — Week 28",
        "body": (
            "Hi team, quick status update for Week 28:\n"
            "Completed: login page redesign, API rate limiting, unit test coverage to 82%.\n"
            "In progress: payment gateway integration (ETA next week).\n"
            "Blocked: staging deploy — waiting for DevOps to fix the CI runner.\n"
            "Overall: on track for the July 25 release."
        ),
        "expect": False,
        "expect_type": None,
    },
    {
        "id": "NEG04",
        "subject": "Complaint — delayed shipment",
        "body": (
            "I placed order #ORD-8821 on June 15 and was promised delivery by June 22. "
            "It is now July 1 and the order has not arrived. I have contacted support twice "
            "with no resolution. I expect a full refund or overnight delivery immediately."
        ),
        "expect": False,
        "expect_type": None,
    },
    {
        "id": "NEG05",
        "subject": "July newsletter — product updates",
        "body": (
            "Welcome to the July edition of the TechCo newsletter!\n\n"
            "New features: dark mode, bulk export, and Zapier integration.\n"
            "Upcoming: custom dashboards launch August 15.\n"
            "Blog: '5 ways to improve your workflow' — read it on our blog.\n"
            "Community: join our Slack workspace with 10,000+ members."
        ),
        "expect": False,
        "expect_type": None,
    },
    {
        "id": "NEG06",
        "subject": "Can you review the attached contract?",
        "body": (
            "Hi, could you take a look at the attached vendor contract and flag any issues "
            "with the SLA terms? I'd like to have it signed by end of week if possible. Thanks."
        ),
        "expect": False,
        "expect_type": None,
    },
]

SEP = "-" * 70


def _check(em: dict, result: dict) -> list[str]:
    issues: list[str] = []
    got = result.get("has_flowchart", False)
    exp = em["expect"]

    if got != exp:
        issues.append(f"has_flowchart expected={exp} got={got}")
        return issues  # structural failure — skip further checks

    if not exp:
        return issues

    nodes = result.get("nodes", [])
    edges = result.get("edges", [])

    if not (3 <= len(nodes) <= 10):
        issues.append(f"node count {len(nodes)} outside [3, 10]")

    bad_types = [n["type"] for n in nodes if n.get("type") not in VALID_NODE_TYPES]
    if bad_types:
        issues.append(f"invalid node types: {bad_types}")

    start_nodes = [n for n in nodes if n.get("type") == "start"]
    if len(start_nodes) != 1:
        issues.append(f"expected exactly 1 start node, got {len(start_nodes)}")

    valid_ids = {n["id"] for n in nodes}
    bad_edges = [
        (e.get("source"), e.get("target"))
        for e in edges
        if e.get("source") not in valid_ids or e.get("target") not in valid_ids
    ]
    if bad_edges:
        issues.append(f"edges reference unknown node ids: {bad_edges}")

    mermaid = result.get("mermaid", "")
    if not mermaid.startswith("flowchart TD"):
        issues.append("mermaid field missing or does not start with 'flowchart TD'")

    exp_type = em.get("expect_type")
    if exp_type and result.get("flowchart_type") != exp_type:
        issues.append(
            f"flowchart_type expected={exp_type} got={result.get('flowchart_type')}"
        )

    return issues


async def run() -> int:
    passes, failures = 0, 0
    print(f"\nFlowchart extraction benchmark on {len(EMAILS)} emails …")
    print(SEP)

    for em in EMAILS:
        result = await detect_flowchart(em["subject"], em["body"])
        await asyncio.sleep(0.4)

        issues = _check(em, result)
        ok = len(issues) == 0

        if ok:
            passes += 1
            status = "PASS"
        else:
            failures += 1
            status = "FAIL"

        fc = result.get("has_flowchart", False)
        ncount = len(result.get("nodes", []))
        ecount = len(result.get("edges", []))
        ftype = result.get("flowchart_type") or "-"

        print(
            f"  {em['id']}  {status}  "
            f"has_flowchart={fc}  type={ftype}  nodes={ncount}  edges={ecount}"
        )
        for issue in issues:
            print(f"    x {issue}")

    total = len(EMAILS)
    print(SEP)
    pct = passes / total * 100
    print(f"Result: {passes}/{total} = {pct:.0f}%  (target >= 13/15 = 87%)")
    print("BENCHMARK PASSED" if passes >= 13 else "BENCHMARK FAILED")
    return failures


if __name__ == "__main__":
    failures = asyncio.run(run())
    sys.exit(0 if failures <= 2 else 1)
