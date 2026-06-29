import pytest

SAMPLE = {
    "email_id": "test-001",
    "subject": "Project Update",
    "body": "Dear team, I wanted to update you on the project status. Please review.",
    "sender": "manager@example.com",
}

VALID_SENTIMENTS = {"positive", "neutral", "negative"}
VALID_TONES = {"formal", "informal", "urgent", "friendly"}


def test_analyze_returns_200(client):
    assert client.post("/api/v1/analyze", json=SAMPLE).status_code == 200


def test_analyze_response_shape(client):
    data = client.post("/api/v1/analyze", json=SAMPLE).json()
    assert data["email_id"] == SAMPLE["email_id"]
    assert isinstance(data["summary"], str) and data["summary"]
    assert isinstance(data["action_items"], list)
    assert isinstance(data["quick_replies"], list)
    assert isinstance(data["grammar_issues"], list)


def test_sentiment_valid_value(client):
    data = client.post("/api/v1/analyze", json=SAMPLE).json()
    assert data["sentiment"] in VALID_SENTIMENTS


def test_tone_valid_value(client):
    data = client.post("/api/v1/analyze", json=SAMPLE).json()
    assert data["tone"] in VALID_TONES


def test_grammar_issues_is_list_of_strings(client):
    data = client.post("/api/v1/analyze", json=SAMPLE).json()
    assert all(isinstance(i, str) for i in data["grammar_issues"])


def test_analyze_without_sender(client):
    payload = {k: v for k, v in SAMPLE.items() if k != "sender"}
    assert client.post("/api/v1/analyze", json=payload).status_code == 200


def test_analyze_missing_required_fields_returns_422(client):
    assert client.post("/api/v1/analyze", json={"email_id": "x"}).status_code == 422


def test_quick_replies_are_non_empty_strings(client):
    replies = client.post("/api/v1/analyze", json=SAMPLE).json()["quick_replies"]
    assert len(replies) > 0
    assert all(isinstance(r, str) and r for r in replies)
