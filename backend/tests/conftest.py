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


async def _fake_translate_text(text: str, target_language: str) -> dict:
    return {
        "translated_text": f"[{target_language.upper()}] {text[:80]}",
        "source_language": "English",
    }


async def _fake_rewrite_tone(text: str, tone: str) -> dict:
    truncated = len(text) > 2_000
    return {
        "rewritten": f"[{tone.upper()}] {text[:120]}",
        "changes_summary": f"Rewrote the email in a {tone} tone.",
        "truncated": truncated,
    }


@pytest.fixture(autouse=True)
def mock_openai():
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=_fake_create)
    with (
        patch("app.routers.analyze.get_client", return_value=mock_client),
        patch("app.routers.grammar.check_grammar", side_effect=_fake_check_grammar),
        patch("app.routers.tone.rewrite_tone", side_effect=_fake_rewrite_tone),
        patch("app.routers.translate.translate_text", side_effect=_fake_translate_text),
    ):
        yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
