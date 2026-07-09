import json

from app.openai_client import get_client

LONG_EMAIL_THRESHOLD_WORDS = 300
_MAX_INPUT_CHARS = 4_000  # generous ceiling (~600 words) for very long emails

_SYSTEM = (
    "You are an expert email analyst. Read the email and distil it into 3–5 concise bullet points.\n"
    "Rules for each bullet:\n"
    "- One key piece of information, decision, request, or deadline per bullet\n"
    "- A complete sentence of 10–25 words\n"
    "- Order from most to least important\n"
    "- Preserve exact names, numbers, dates, and deadlines verbatim\n"
    "- Omit greetings, sign-offs, and pleasantries\n"
    'Return ONLY a JSON object with one key: "bullets" — an array of 3–5 strings.\n'
    'Do NOT prefix the strings with "•", "-", or any other bullet character.'
)


def _word_count(text: str) -> int:
    return len(text.split())


def is_long_email(text: str) -> bool:
    return _word_count(text) >= LONG_EMAIL_THRESHOLD_WORDS


async def summarize_email(text: str) -> dict:
    word_count = _word_count(text)

    if word_count < LONG_EMAIL_THRESHOLD_WORDS:
        return {"bullets": [], "word_count": word_count, "was_summarized": False}

    working_text = text[:_MAX_INPUT_CHARS]

    resp = await get_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": f"Email to summarize:\n{working_text}"},
        ],
        max_tokens=512,
        temperature=0.2,
    )

    data = json.loads(resp.choices[0].message.content)
    raw_bullets = data.get("bullets", [])

    # Strip any leading bullet chars the model may add despite instructions
    bullets = [
        b.lstrip("••–—- ").strip()
        for b in raw_bullets
        if isinstance(b, str) and b.strip()
    ]

    return {
        "bullets": bullets[:5],
        "word_count": word_count,
        "was_summarized": True,
    }
