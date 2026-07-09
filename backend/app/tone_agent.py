import json

from app.models import ToneVariant
from app.openai_client import get_client

_MAX_INPUT_CHARS = 2_000   # clip long emails to avoid blowing the output budget
_SHORT_THRESHOLD = 100     # emails shorter than this need special handling

_SYSTEM = (
    "You are an expert email writer. Rewrite the given email in the requested tone. "
    "Return a JSON object with:\n"
    "- rewritten: the full rewritten email text\n"
    "- changes_summary: one sentence describing the key changes made"
)

_TONE_INSTRUCTIONS: dict[ToneVariant, str] = {
    "formal": (
        "Rewrite in a formal, professional tone. Use complete sentences, avoid contractions, "
        "maintain respectful distance, and structure the text clearly. "
        "Begin with a proper salutation and close with a professional sign-off."
    ),
    "friendly": (
        "Rewrite in a warm, friendly tone. Be conversational and approachable — "
        "contractions are fine, use the reader's first name if present, and keep it "
        "personal while still being professional."
    ),
    "concise": (
        "Rewrite to be concise and direct. Remove all filler words, redundant phrases, "
        "and unnecessary details. Keep only what is essential. "
        "Aim for 40–50% fewer words than the original. "
        "If the email is already very short, preserve its brevity — do not pad it."
    ),
    "persuasive": (
        "Rewrite to be persuasive and compelling. Lead with the benefit to the reader, "
        "use the rule of three for key points, build toward a clear call to action, "
        "and create mild urgency without being pushy. "
        "Keep the tone professional but enthusiastic."
    ),
    "executive": (
        "Rewrite in an executive style. Apply BLUF (Bottom Line Up Front): state the "
        "decision or request in the first sentence. Follow with 2–3 bullet points for "
        "supporting context. Close with a single, unambiguous action item and deadline "
        "if one is implied. No pleasantries, no padding."
    ),
    "professional": (
        "Perform a full professional rewrite. Apply all of the following:\n"
        "1. Lead with the key point (BLUF structure)\n"
        "2. Formal language — no contractions, no slang\n"
        "3. Fix all grammar, spelling, and punctuation\n"
        "4. Remove all filler words and redundancy\n"
        "5. Use bullet points for any list of three or more items\n"
        "6. Close with a clear call to action if one is implied\n"
        "This is the highest-quality rewrite mode — be thorough."
    ),
}

# Appended to the instruction for very short emails to prevent padding
_SHORT_ADDENDUM = (
    " IMPORTANT: this email is very short — do not add content that was not implied "
    "by the original. Preserve its brevity."
)


async def rewrite_tone(text: str, tone: ToneVariant) -> dict:
    truncated = len(text) > _MAX_INPUT_CHARS
    working_text = text[:_MAX_INPUT_CHARS] if truncated else text

    instruction = _TONE_INSTRUCTIONS[tone]
    if len(working_text.strip()) < _SHORT_THRESHOLD:
        instruction += _SHORT_ADDENDUM

    # Long emails need more output tokens; short ones need fewer
    max_tokens = 1_500 if len(working_text) > 1_000 else 768

    resp = await get_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": f"Tone: {tone}\nInstruction: {instruction}\n\nEmail:\n{working_text}"},
        ],
        max_tokens=max_tokens,
        temperature=0.4,
    )
    data = json.loads(resp.choices[0].message.content)
    data["truncated"] = truncated
    return data
