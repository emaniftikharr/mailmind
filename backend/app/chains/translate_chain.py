"""
LCEL chain: email translation.

Uses llama-3.3-70b-versatile for quality.
Template vars: {target_language}, {language_hint}, {email_text}
language_hint may be an empty string when no per-language override exists.
"""
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.runnables import Runnable

from app.chains.base import get_groq_llm_large

MAX_INPUT_CHARS = 3_000

_SYSTEM = """\
You are a professional business email translator.
Translate the given email text preserving these properties:
1. Formatting: paragraph breaks, bullet points, numbered lists
2. Email addresses, URLs, proper nouns, and brand names — leave unchanged
3. The original register (formal stays formal, casual stays casual)
4. Salutations and sign-offs adapted to target-language conventions
Do NOT add translator notes, bracketed explanations, or disclaimers.
Respond with valid JSON only — no prose, no markdown fences.

OUTPUT SCHEMA
{
  "translated_text":  <string — complete translated email>,
  "source_language":  <string — detected source language, e.g. "English">
}
"""

_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=_SYSTEM),
    HumanMessagePromptTemplate.from_template(
        "Target language: {target_language}\n"
        "{language_hint}"
        "\nEmail to translate:\n{email_text}"
    ),
])

_chain: Runnable | None = None


def get_translate_chain() -> Runnable:
    global _chain
    if _chain is None:
        llm = get_groq_llm_large(temperature=0.1, max_tokens=1_024)
        _chain = (_prompt | llm | JsonOutputParser()).with_retry(
            stop_after_attempt=3,
        )
    return _chain
