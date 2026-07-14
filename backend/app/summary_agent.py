from app.chains.summary_chain import (
    MAX_INPUT_CHARS,
    WORD_THRESHOLD,
    get_summary_chain,
)


def _word_count(text: str) -> int:
    return len(text.split())


def is_long_email(text: str) -> bool:
    return _word_count(text) >= WORD_THRESHOLD


async def summarize_email(text: str) -> dict:
    word_count = _word_count(text)

    if word_count < WORD_THRESHOLD:
        return {"bullets": [], "word_count": word_count, "was_summarized": False}

    data: dict = await get_summary_chain().ainvoke(
        {"email_text": text[:MAX_INPUT_CHARS]}
    )
    raw_bullets = data.get("bullets", [])

    bullets = [
        b.lstrip("•–—- ").strip()
        for b in raw_bullets
        if isinstance(b, str) and b.strip()
    ]

    return {
        "bullets": bullets[:5],
        "word_count": word_count,
        "was_summarized": True,
    }
