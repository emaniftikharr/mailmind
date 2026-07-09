import json

from app.openai_client import get_client

_MAX_INPUT_CHARS = 4_000  # mirrors translate_agent; prevents context-window overflow

_SYSTEM = (
    "You are a professional copy editor. The user will give you a block of text. "
    "Identify all grammar, spelling, punctuation, and style issues. "
    "Return a JSON object with exactly these fields:\n"
    "- corrected_text: the full corrected version of the input text\n"
    "- corrections: array of objects, each with:\n"
    "    - original: the exact phrase that was wrong (as it appears in the input)\n"
    "    - corrected: the replacement phrase\n"
    "    - explanation: one short sentence explaining the fix\n"
    "Return an empty corrections array if the text has no issues."
)


async def check_grammar(text: str) -> dict:
    resp = await get_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": text[:_MAX_INPUT_CHARS]},
        ],
        max_tokens=1024,
        temperature=0.2,
    )
    return json.loads(resp.choices[0].message.content)
