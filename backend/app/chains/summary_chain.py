"""
LCEL chain: email bullet-point summarisation.

Uses llama-3.3-70b-versatile for quality; only triggered for emails >= 300 words.
"""
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.runnables import Runnable

from app.chains.base import get_groq_llm_large

MAX_INPUT_CHARS = 4_000
WORD_THRESHOLD  = 300

_SYSTEM = """\
You are an expert email analyst. Read the email and distil it into 3-5 concise bullet points.
Respond with valid JSON only — no prose, no markdown fences.

OUTPUT SCHEMA
{"bullets": ["<bullet 1>", "<bullet 2>", ...]}

RULES
- One key piece of information, decision, request, or deadline per bullet.
- Each bullet is a complete sentence of 10-25 words.
- Order from most to least important.
- Preserve exact names, numbers, dates, and deadlines verbatim.
- Omit greetings, sign-offs, and pleasantries.
- Do NOT prefix bullets with "•", "-", or any other character.
- Return between 3 and 5 bullets — never fewer, never more.
"""

_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=_SYSTEM),
    HumanMessagePromptTemplate.from_template("Email to summarize:\n{email_text}"),
])

_chain: Runnable | None = None


def get_summary_chain() -> Runnable:
    global _chain
    if _chain is None:
        llm = get_groq_llm_large(temperature=0.2, max_tokens=512)
        _chain = (_prompt | llm | JsonOutputParser()).with_retry(
            stop_after_attempt=3,
        )
    return _chain
