import pytest

from app.models import SUPPORTED_LANGUAGES

TEXT = "Hello, how are you doing today?"


@pytest.mark.parametrize("language", list(SUPPORTED_LANGUAGES.keys()))
def test_translate_all_supported_languages(client, language):
    resp = client.post("/api/v1/translate", json={"text": TEXT, "target_language": language})
    assert resp.status_code == 200
    data = resp.json()
    assert data["target_language"] == language
    assert data["source_language"] == "English"
    assert isinstance(data["translated_text"], str) and data["translated_text"]


def test_translate_unsupported_language_returns_422(client):
    resp = client.post("/api/v1/translate", json={"text": TEXT, "target_language": "Klingon"})
    assert resp.status_code == 422


def test_translate_missing_target_language_returns_422(client):
    assert client.post("/api/v1/translate", json={"text": TEXT}).status_code == 422


def test_translate_missing_text_returns_422(client):
    assert client.post("/api/v1/translate", json={"target_language": "Spanish"}).status_code == 422


def test_translate_response_shape(client):
    resp = client.post("/api/v1/translate", json={"text": TEXT, "target_language": "French"})
    data = resp.json()
    assert "translated_text" in data
    assert "source_language" in data
    assert "target_language" in data


def test_supported_languages_count():
    assert len(SUPPORTED_LANGUAGES) == 5


def test_supported_languages_have_iso_codes():
    assert all(len(code) == 2 for code in SUPPORTED_LANGUAGES.values())
