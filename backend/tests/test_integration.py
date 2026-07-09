"""
Phase 1 integration tests — five Gmail account personas.

Persona overview:
  corporate   – formal, 300+ word email, multiple action items
  startup     – extremely short, casual, no punctuation
  international – English with grammar errors, ~80 words
  digest      – long structured newsletter, 300+ words
  minimalist  – 5-word terse reply
"""

import pytest

from app.summary_agent import LONG_EMAIL_THRESHOLD_WORDS

# ── Gmail account personas ─────────────────────────────────────────────────────

_CORPORATE = {
    "email_id": "corp-001",
    "subject": "Q4 Board Presentation Review — Action Required Before Friday",
    "sender": "patricia.moore@acmecorp.com",
    "body": (
        "Dear Jennifer and team,\n\n"
        "I am reaching out to outline the preparation requirements for our Q4 board "
        "presentation scheduled for Friday, November 15th at 2:00 PM in the Sequoia "
        "Conference Room. Given the significance of this presentation to our Series B "
        "fundraising discussions, I want to ensure every aspect is thoroughly prepared.\n\n"
        "The presentation will run ninety minutes and cover Q3 financial performance versus "
        "plan, Q4 pipeline and forecast, product roadmap update for 2025, competitive "
        "landscape analysis, team and headcount overview, and key risks and mitigations.\n\n"
        "Robert Chen is responsible for the financial slides covering Q3 actuals, burn rate, "
        "runway analysis, and Q4 projections. These slides must be submitted for review by "
        "Wednesday noon. Lisa Nakamura owns the sales pipeline and ARR summary. The revenue "
        "section must reflect Salesforce data as of this morning's snapshot. Marcus Rivera "
        "will present the engineering and product roadmap, including the MailMind v2.0 launch "
        "results and v3.0 planning milestones. The People section covering headcount, "
        "attrition, and diversity initiatives will be owned by Rachel Turner.\n\n"
        "We will send board members a ten-page pre-read document by Thursday morning. This "
        "should include the executive summary, Q3 financial package, and one-page product "
        "update. Amanda Torres will coordinate distribution via BoardVantage by 9 AM Thursday.\n\n"
        "We will hold a full run-through on Thursday at 4 PM in Redwood. All presenters are "
        "required to attend. Each section owner should time their section during rehearsal to "
        "ensure we stay within the ninety-minute window. Coffee and lunch will be provided.\n\n"
        "All slides must be submitted to me by Wednesday noon so I can compile the master "
        "deck. Please review the board materials checklist in Notion and confirm your section "
        "is complete. If you have any questions, please reach out before Wednesday morning.\n\n"
        "Thank you for your continued dedication.\n\n"
        "Best regards,\nPatricia Moore\nChief of Staff"
    ),
}

_STARTUP = {
    "email_id": "startup-001",
    "subject": "re: deploy",
    "sender": "mike@startup.io",
    "body": "deployed to staging. looks good. want me to push to prod now or wait for ur review?",
}

_INTL = {
    "email_id": "intl-001",
    "subject": "Questions about the contract",
    "sender": "pierre@europe-example.fr",
    "body": (
        "Dear Sir or Madam, I am writing you to ask some question about the contract we have "
        "sign last month. There is some points which is not very clear for me. First, what it "
        "mean when we say delivery in 30 days? Is it 30 calendar day or 30 working day? "
        "Second, the price we have agree, it include the tax yes or no? Also I want to know "
        "who is the contact person for the support if we have problem after the delivery. "
        "Please can you send to me the notes of the meeting when you have them ready. "
        "Thank you very much for your comprehension and your help in this matter."
    ),
}

_DIGEST = {
    "email_id": "digest-001",
    "subject": "Weekly Product Digest — 12 Updates This Week",
    "sender": "noreply@digest.example.com",
    "body": (
        "This week's product digest covers twelve updates across engineering, design, and "
        "customer success. Below is a summary of each initiative and its current status.\n\n"
        "Feature Updates:\n"
        "The AI email summarization feature shipped to 100% of users on Monday following a "
        "successful two-week beta. Initial data shows a 34% increase in user engagement with "
        "the AI features panel. The smart thread grouping algorithm was updated to better "
        "handle forwarded emails. Users reported a 12% reduction in misclassified threads.\n\n"
        "The mobile app redesign is now in final QA. The new navigation structure reduces "
        "average tap depth for common actions from 4.2 taps to 2.1 taps. Target release date "
        "remains November 22nd. Enterprise SSO integration passed security certification on "
        "Tuesday. The feature will be available to enterprise customers on December 1st "
        "following a controlled rollout to prevent support overload.\n\n"
        "Engineering Updates:\n"
        "The database migration to PostgreSQL 16 completed without incidents during Sunday's "
        "maintenance window. Query performance on the inbox view improved by 28%. The CI/CD "
        "pipeline now runs parallel test suites, reducing average build time from 14 minutes "
        "to 6 minutes. The infrastructure team completed the autoscaling policy audit following "
        "the October 14th production incident. All policies have been reviewed and corrected.\n\n"
        "Customer Success:\n"
        "Three new enterprise customers went live this week: Meridian Healthcare, Cascade "
        "Financial, and TerraVerde Logistics. Combined ARR impact is $840,000. Customer churn "
        "for October came in at 1.2%, below our 1.5% target. The top reasons cited in exit "
        "interviews were cost and missing mobile features, both of which the upcoming redesign "
        "directly addresses.\n\n"
        "Team Updates:\n"
        "Michael Torres joined the Platform Engineering team this week as Senior Software "
        "Engineer. Welcome Michael! Two engineering positions remain open. Looking ahead to "
        "next week, the product leadership team will finalize the 2025 roadmap. Results will "
        "be shared company-wide at the all-hands meeting on November 20th."
    ),
}

_MINIMAL = {
    "email_id": "min-001",
    "subject": "Done",
    "sender": "jo@team.com",
    "body": "Completed the review. LGTM.",
}

# Module-level word-count sanity checks
assert len(_CORPORATE["body"].split()) >= LONG_EMAIL_THRESHOLD_WORDS
assert len(_DIGEST["body"].split()) >= LONG_EMAIL_THRESHOLD_WORDS
assert len(_STARTUP["body"].split()) < LONG_EMAIL_THRESHOLD_WORDS
assert len(_INTL["body"].split()) < LONG_EMAIL_THRESHOLD_WORDS
assert len(_MINIMAL["body"].split()) < LONG_EMAIL_THRESHOLD_WORDS

ALL_PERSONAS = [
    pytest.param(_CORPORATE, id="corporate"),
    pytest.param(_STARTUP,   id="startup"),
    pytest.param(_INTL,      id="international"),
    pytest.param(_DIGEST,    id="digest"),
    pytest.param(_MINIMAL,   id="minimalist"),
]

LONG_PERSONAS = [
    pytest.param(_CORPORATE, id="corporate"),
    pytest.param(_DIGEST,    id="digest"),
]

SHORT_PERSONAS = [
    pytest.param(_STARTUP,   id="startup"),
    pytest.param(_INTL,      id="international"),
    pytest.param(_MINIMAL,   id="minimalist"),
]

VALID_SENTIMENTS = {"positive", "neutral", "negative"}
VALID_TONES_ANALYZE = {"formal", "informal", "urgent", "friendly"}


# ── Health ────────────────────────────────────────────────────────────────────

def test_health_returns_ok(client):
    assert client.get("/health").json()["status"] == "ok"


def test_health_has_positive_uptime(client):
    assert client.get("/health").json()["uptime_seconds"] >= 0


# ── Analyze ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("persona", ALL_PERSONAS)
def test_analyze_all_personas_returns_200(client, persona):
    assert client.post("/api/v1/analyze", json=persona).status_code == 200


@pytest.mark.parametrize("persona", ALL_PERSONAS)
def test_analyze_all_personas_echoes_email_id(client, persona):
    data = client.post("/api/v1/analyze", json=persona).json()
    assert data["email_id"] == persona["email_id"]


@pytest.mark.parametrize("persona", ALL_PERSONAS)
def test_analyze_all_personas_sentiment_valid(client, persona):
    assert client.post("/api/v1/analyze", json=persona).json()["sentiment"] in VALID_SENTIMENTS


@pytest.mark.parametrize("persona", ALL_PERSONAS)
def test_analyze_all_personas_tone_valid(client, persona):
    assert client.post("/api/v1/analyze", json=persona).json()["tone"] in VALID_TONES_ANALYZE


@pytest.mark.parametrize("persona", ALL_PERSONAS)
def test_analyze_all_personas_lists_are_lists(client, persona):
    data = client.post("/api/v1/analyze", json=persona).json()
    assert isinstance(data["action_items"], list)
    assert isinstance(data["quick_replies"], list)
    assert isinstance(data["grammar_issues"], list)


def test_analyze_without_optional_sender(client):
    payload = {k: v for k, v in _CORPORATE.items() if k != "sender"}
    assert client.post("/api/v1/analyze", json=payload).status_code == 200


# ── Grammar ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("persona", ALL_PERSONAS)
def test_grammar_all_personas_returns_200(client, persona):
    assert client.post("/api/v1/grammar", json={"text": persona["body"]}).status_code == 200


@pytest.mark.parametrize("persona", ALL_PERSONAS)
def test_grammar_all_personas_corrected_text_is_string(client, persona):
    data = client.post("/api/v1/grammar", json={"text": persona["body"]}).json()
    assert isinstance(data["corrected_text"], str) and data["corrected_text"]


def test_grammar_international_has_corrections(client):
    data = client.post("/api/v1/grammar", json={"text": _INTL["body"]}).json()
    assert len(data["corrections"]) > 0
    for c in data["corrections"]:
        assert isinstance(c["original"], str) and c["original"]
        assert isinstance(c["corrected"], str) and c["corrected"]
        assert isinstance(c["explanation"], str) and c["explanation"]


# ── Tone ──────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("persona", ALL_PERSONAS)
def test_tone_formal_all_personas_200(client, persona):
    resp = client.post("/api/v1/rewrite-tone",
                       json={"text": persona["body"], "tone": "formal"})
    assert resp.status_code == 200


@pytest.mark.parametrize("tone", ["concise", "executive", "professional"])
def test_tone_variants_on_corporate_email(client, tone):
    data = client.post("/api/v1/rewrite-tone",
                       json={"text": _CORPORATE["body"], "tone": tone}).json()
    assert isinstance(data["rewritten"], str) and data["rewritten"]
    assert data["tone"] == tone
    assert isinstance(data["truncated"], bool)


def test_tone_concise_on_startup_not_truncated(client):
    data = client.post("/api/v1/rewrite-tone",
                       json={"text": _STARTUP["body"], "tone": "concise"}).json()
    assert data["truncated"] is False


# ── Translate ─────────────────────────────────────────────────────────────────

_TRANSLATE_LANGUAGES = ["Spanish", "French", "German", "Portuguese", "Japanese"]

@pytest.mark.parametrize("persona,language", list(zip(
    [_CORPORATE, _STARTUP, _INTL, _DIGEST, _MINIMAL],
    _TRANSLATE_LANGUAGES,
)), ids=[f"{p['email_id']}->{l}" for p, l in zip(
    [_CORPORATE, _STARTUP, _INTL, _DIGEST, _MINIMAL],
    _TRANSLATE_LANGUAGES,
)])
def test_translate_one_language_per_persona(client, persona, language):
    resp = client.post("/api/v1/translate",
                       json={"text": persona["body"], "target_language": language})
    assert resp.status_code == 200
    data = resp.json()
    assert data["target_language"] == language
    assert isinstance(data["translated_text"], str) and data["translated_text"]


# ── Summarize ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("persona", LONG_PERSONAS)
def test_summarize_long_personas_was_summarized(client, persona):
    data = client.post("/api/v1/summarize", json={"text": persona["body"]}).json()
    assert data["was_summarized"] is True
    assert data["word_count"] >= LONG_EMAIL_THRESHOLD_WORDS


@pytest.mark.parametrize("persona", LONG_PERSONAS)
def test_summarize_long_personas_valid_bullets(client, persona):
    data = client.post("/api/v1/summarize", json={"text": persona["body"]}).json()
    assert 3 <= len(data["bullets"]) <= 5
    assert all(isinstance(b, str) and b for b in data["bullets"])


@pytest.mark.parametrize("persona", SHORT_PERSONAS)
def test_summarize_short_personas_not_summarized(client, persona):
    data = client.post("/api/v1/summarize", json={"text": persona["body"]}).json()
    assert data["was_summarized"] is False
    assert data["bullets"] == []
