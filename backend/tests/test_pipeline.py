"""
End-to-end pipeline test — backend/tests/test_pipeline.py

Fires run_pipeline() on 3 representative emails and checks that every
section of the unified response is structurally complete.

Run: python backend/tests/test_pipeline.py
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

from app.pipeline_agent import run_pipeline

EMAILS = [
    {
        "id": "P01",
        "subject": "Urgent: system outage affecting production",
        "body": (
            "Hi team, we have a critical outage on the payments service. "
            "All transactions are failing since 14:00 UTC. "
            "Engineering is investigating — please join the war room call immediately. "
            "Zoom link: zoom.us/j/12345. ETA for resolution: 1 hour."
        ),
        "sender": "oncall@company.com",
        "expect_category": None,        # any is fine
        "expect_priority": "urgent",
        "expect_reply_needed": True,
        "expect_has_tasks": True,
    },
    {
        "id": "P02",
        "subject": "Team lunch on Friday — please RSVP",
        "body": (
            "Hey everyone! We're doing a team lunch this Friday at 12:30 PM at The Ivy. "
            "Please reply with your dietary requirements by Thursday. "
            "Looking forward to seeing you all!"
        ),
        "sender": "alice@company.com",
        "expect_category": None,
        "expect_priority": None,
        "expect_reply_needed": True,
        "expect_has_tasks": None,
    },
    {
        "id": "P03",
        "subject": "Your Amazon order #113-2233445 has shipped",
        "body": (
            "Hello, your order has shipped and will arrive by Thursday July 17. "
            "Track your package at amazon.com/tracking. "
            "No action required."
        ),
        "sender": "noreply@amazon.com",
        "expect_category": None,
        "expect_priority": None,
        "expect_reply_needed": False,
        "expect_has_tasks": None,
    },
]

SEP = "-" * 68

REQUIRED_KEYS = {
    "classification": {"category", "priority", "confidence", "reason"},
    "phishing":       {"verdict", "risk_score", "safe_to_open"},
    "trust":          {"trust_score", "risk_level", "summary"},
    "links":          {"links", "total", "flagged", "risk_flags"},
    "actions":        {"meeting", "deadlines", "tasks", "has_meeting"},
    "replies":        {"variants", "count", "reply_needed"},
}


def _check_result(em: dict, result: dict) -> list[str]:
    issues: list[str] = []

    for section, keys in REQUIRED_KEYS.items():
        data = result.get(section)
        if not isinstance(data, dict):
            issues.append(f"[{section}] missing or not a dict")
            continue
        for k in keys:
            if k not in data:
                issues.append(f"[{section}] missing key '{k}'")

    # Spot-check expectations
    c = result.get("classification", {})
    r = result.get("replies", {})

    if em["expect_priority"] and c.get("priority") != em["expect_priority"]:
        issues.append(
            f"[classification] priority expected={em['expect_priority']} got={c.get('priority')}"
        )

    if em["expect_reply_needed"] is not None:
        if r.get("reply_needed") != em["expect_reply_needed"]:
            issues.append(
                f"[replies] reply_needed expected={em['expect_reply_needed']} "
                f"got={r.get('reply_needed')}"
            )

    if em["expect_has_tasks"] is not None:
        a = result.get("actions", {})
        if a.get("has_tasks") != em["expect_has_tasks"]:
            issues.append(
                f"[actions] has_tasks expected={em['expect_has_tasks']} got={a.get('has_tasks')}"
            )

    return issues


async def run() -> int:
    failures = 0
    print(f"\nRunning pipeline on {len(EMAILS)} emails …")
    print(SEP)

    for em in EMAILS:
        result = await run_pipeline(
            em["subject"], em["body"], sender=em["sender"]
        )
        await asyncio.sleep(0.5)

        c = result.get("classification", {})
        r = result.get("replies", {})
        a = result.get("actions", {})
        p = result.get("phishing", {})
        t = result.get("trust", {})
        elapsed = result.get("elapsed_ms", "?")

        issues = _check_result(em, result)

        status = "FAIL" if issues else "PASS"
        print(
            f"\n  {em['id']}  {status}  {elapsed}ms\n"
            f"    classify : {c.get('category','?')} / {c.get('priority','?')}  "
            f"(conf={c.get('confidence',0):.2f})\n"
            f"    phishing : verdict={p.get('verdict','?')}  "
            f"risk={p.get('risk_score','?')}\n"
            f"    trust    : score={t.get('trust_score','?')}  "
            f"level={t.get('risk_level','?')}\n"
            f"    actions  : meeting={a.get('has_meeting','?')}  "
            f"tasks={a.get('has_tasks','?')}  "
            f"deadlines={a.get('has_deadlines','?')}\n"
            f"    replies  : needed={r.get('reply_needed','?')}  "
            f"count={r.get('count','?')}"
        )
        for issue in issues:
            print(f"    ✗ {issue}")
            failures += 1

    print(f"\n{SEP}")
    print(f"Total failures: {failures}  (pass threshold: 0)")
    print("PIPELINE TEST PASSED" if failures == 0 else "PIPELINE TEST FAILED")
    return failures


if __name__ == "__main__":
    failures = asyncio.run(run())
    sys.exit(0 if failures == 0 else 1)
