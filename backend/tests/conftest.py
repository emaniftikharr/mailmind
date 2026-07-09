import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

_ANALYZE_JSON = json.dumps({
    "summary": "This is a test summary of the email.",
    "action_items": ["Review the email content", "Reply within 24 hours"],
    "quick_replies": [
        "Thanks, I'll look into this.",
        "Could you provide more details?",
        "Sounds good, let's proceed.",
    ],
    "sentiment": "neutral",
    "tone": "formal",
    "grammar_issues": [],
})

_GRAMMAR_DATA = {
    "corrected_text": "I wanted to update you on the project status.",
    "corrections": [
        {
            "original": "i wanted",
            "corrected": "I wanted",
            "explanation": "Sentences must begin with a capital letter.",
        }
    ],
}


def _make_response(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


async def _fake_create(model, messages, **kwargs):
    return _make_response(_ANALYZE_JSON)


async def _fake_check_grammar(text: str) -> dict:
    return _GRAMMAR_DATA


@pytest.fixture(autouse=True)
def mock_openai():
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=_fake_create)
    with (
        patch("app.routers.analyze.get_client", return_value=mock_client),
        patch("app.routers.grammar.check_grammar", side_effect=_fake_check_grammar),
    ):
        yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
