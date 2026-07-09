import pytest

TEXT = "i wanted to update you on the project status."


def test_grammar_returns_200(client):
    assert client.post("/api/v1/grammar", json={"text": TEXT}).status_code == 200


def test_grammar_response_shape(client):
    data = client.post("/api/v1/grammar", json={"text": TEXT}).json()
    assert "corrected_text" in data
    assert "corrections" in data
    assert isinstance(data["corrections"], list)


def test_grammar_corrected_text_is_string(client):
    data = client.post("/api/v1/grammar", json={"text": TEXT}).json()
    assert isinstance(data["corrected_text"], str)
    assert len(data["corrected_text"]) > 0


def test_grammar_correction_fields(client):
    corrections = client.post("/api/v1/grammar", json={"text": TEXT}).json()["corrections"]
    assert len(corrections) > 0
    for c in corrections:
        assert isinstance(c["original"], str)
        assert isinstance(c["corrected"], str)
        assert isinstance(c["explanation"], str)


def test_grammar_missing_text_returns_422(client):
    assert client.post("/api/v1/grammar", json={}).status_code == 422
