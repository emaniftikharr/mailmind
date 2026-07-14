from app.chains.translate_chain import MAX_INPUT_CHARS, get_translate_chain

_LANGUAGE_HINTS: dict[str, str] = {
    "Spanish":    "Formal register, usted form. Standard international Spanish.",
    "French":     "Formal register, vous form. Standard metropolitan French.",
    "German":     "Formal register, Sie form. Standard Hochdeutsch.",
    "Portuguese": "Formal European Portuguese (not Brazilian). Avoid gírias.",
    "Japanese":   "Use keigo (丁寧語 / 敬語) appropriate for business correspondence.",
}


async def translate_text(text: str, target_language: str) -> dict:
    hint = _LANGUAGE_HINTS.get(target_language, "")
    language_hint_line = f"Language note: {hint}\n" if hint else ""

    return await get_translate_chain().ainvoke(
        {
            "target_language": target_language,
            "language_hint": language_hint_line,
            "email_text": text[:MAX_INPUT_CHARS],
        }
    )
