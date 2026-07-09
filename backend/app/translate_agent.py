import json

from app.openai_client import get_client

_MAX_INPUT_CHARS = 3_000

_SYSTEM = (
    "You are a professional business email translator. "
    "Translate the given email text preserving these properties:\n"
    "1. Formatting: paragraph breaks, bullet points, numbered lists\n"
    "2. Email addresses, URLs, proper nouns, and brand names — leave unchanged\n"
    "3. The original register (formal stays formal, casual stays casual)\n"
    "4. Salutations and sign-offs adapted to target-language conventions\n"
    "Do NOT add translator notes, bracketed explanations, or disclaimers.\n"
    "Return ONLY a JSON object with:\n"
    "- translated_text: the complete translated email\n"
    '- source_language: the detected source language (e.g. "English")'
)

_LANGUAGE_HINTS: dict[str, str] = {
    "Spanish":    "Formal register, usted form. Standard international Spanish.",
    "French":     "Formal register, vous form. Standard metropolitan French.",
    "German":     "Formal register, Sie form. Standard Hochdeutsch.",
    "Portuguese": "Formal European Portuguese (not Brazilian). Avoid gírias.",
    "Japanese":   "Use keigo (丁寧語 / 敬語) appropriate for business correspondence.",
}


async def translate_text(text: str, target_language: str) -> dict:
    hint = _LANGUAGE_HINTS.get(target_language, "")
    working_text = text[:_MAX_INPUT_CHARS]

    user_lines = [f"Target language: {target_language}"]
    if hint:
        user_lines.append(f"Language note: {hint}")
    user_lines.append(f"\nEmail to translate:\n{working_text}")

    resp = await get_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": "\n".join(user_lines)},
        ],
        max_tokens=1_024,
        temperature=0.1,
    )
    return json.loads(resp.choices[0].message.content)
