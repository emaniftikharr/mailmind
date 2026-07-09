import pytest

ALL_TONES = ["formal", "friendly", "concise", "persuasive", "executive", "professional"]

# 5 representative emails covering different real-world scenarios
EMAILS = [
    pytest.param(
        "hey mike, just checking if u got my last email lol. need ur feedback asap thx",
        id="casual-slack-style",
    ),
    pytest.param(
        "Dear Mr. Johnson, I am writing to formally inquire as to whether you have had "
        "the opportunity to review the aforementioned documentation pertaining to the "
        "quarterly financial report that was submitted for your consideration on the "
        "fourteenth of this month.",
        id="overly-formal",
    ),
    pytest.param(
        "Hi Sarah! I wanted to reach out because I was thinking about our project and "
        "I just had SO many thoughts about it. So basically what I was thinking is that "
        "maybe we could potentially consider possibly scheduling a meeting sometime next "
        "week if that works for you and everyone else on the team of course!",
        id="rambling-friendly",
    ),
    pytest.param(
        "This is a follow-up to my previous three emails. I still have not received "
        "a response. The deadline was last Friday. Please confirm receipt and provide "
        "an ETA on the deliverable. This is blocking the entire team.",
        id="urgent-followup",
    ),
    pytest.param(
        "Thank you for your email. I wanted to let you know that I have received your "
        "message and I will do my best to get back to you as soon as I possibly can "
        "within the next few business days when I have had the chance to look into "
        "this matter more thoroughly.",
        id="verbose-acknowledgement",
    ),
]

# ── Core parametrized tests (5 emails × 6 tones = 30 combinations) ──────────

@pytest.mark.parametrize("tone", ALL_TONES)
@pytest.mark.parametrize("email_body", EMAILS)
def test_rewrite_returns_200(client, email_body, tone):
    resp = client.post("/api/v1/rewrite-tone", json={"text": email_body, "tone": tone})
    assert resp.status_code == 200


@pytest.mark.parametrize("tone", ALL_TONES)
@pytest.mark.parametrize("email_body", EMAILS)
def test_rewrite_response_shape(client, email_body, tone):
    data = client.post("/api/v1/rewrite-tone", json={"text": email_body, "tone": tone}).json()
    assert isinstance(data["rewritten"], str) and data["rewritten"]
    assert data["tone"] == tone
    assert isinstance(data["changes_summary"], str) and data["changes_summary"]
    assert isinstance(data["truncated"], bool)


# ── Edge case: short email ────────────────────────────────────────────────────

SHORT_EMAIL = "ok"

@pytest.mark.parametrize("tone", ALL_TONES)
def test_short_email_returns_200(client, tone):
    resp = client.post("/api/v1/rewrite-tone", json={"text": SHORT_EMAIL, "tone": tone})
    assert resp.status_code == 200


@pytest.mark.parametrize("tone", ALL_TONES)
def test_short_email_not_truncated(client, tone):
    data = client.post("/api/v1/rewrite-tone", json={"text": SHORT_EMAIL, "tone": tone}).json()
    assert data["truncated"] is False


# ── Edge case: long email (>2 000 chars) ─────────────────────────────────────

LONG_EMAIL = ("This is a filler sentence for a very long email. " * 60).strip()  # ~3 000 chars

@pytest.mark.parametrize("tone", ALL_TONES)
def test_long_email_returns_200(client, tone):
    resp = client.post("/api/v1/rewrite-tone", json={"text": LONG_EMAIL, "tone": tone})
    assert resp.status_code == 200


@pytest.mark.parametrize("tone", ALL_TONES)
def test_long_email_flagged_truncated(client, tone):
    data = client.post("/api/v1/rewrite-tone", json={"text": LONG_EMAIL, "tone": tone}).json()
    assert data["truncated"] is True


# ── Validation ────────────────────────────────────────────────────────────────

def test_unsupported_tone_returns_422(client):
    resp = client.post("/api/v1/rewrite-tone", json={"text": "Hello", "tone": "aggressive"})
    assert resp.status_code == 422


def test_missing_text_returns_422(client):
    assert client.post("/api/v1/rewrite-tone", json={"tone": "formal"}).status_code == 422


def test_missing_tone_returns_422(client):
    assert client.post("/api/v1/rewrite-tone", json={"text": "Hello"}).status_code == 422
