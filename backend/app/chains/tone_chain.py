"""
LCEL chain: tone rewriting.

Uses llama-3.3-70b-versatile for quality. Two singletons (short / long) so
the max_tokens budget stays proportional to the input length.
"""
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.runnables import Runnable

from app.chains.base import get_groq_llm_large

MAX_INPUT_CHARS = 2_000
SHORT_THRESHOLD = 100   # emails shorter than this get padding-prevention addendum

_SYSTEM = """\
You are an expert email writer. Rewrite the given email in the requested tone.
Respond with valid JSON only — no prose, no markdown fences.

OUTPUT SCHEMA
{
  "rewritten":       <string — the complete rewritten email>,
  "changes_summary": <string — one sentence describing the key changes made>
}

RULES
- Preserve all factual content, names, dates, and numbers exactly.
- Do not add information not present in the original.
- Apply the tone instruction precisely and completely.
"""

_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=_SYSTEM),
    HumanMessagePromptTemplate.from_template(
        "Tone: {tone}\nInstruction: {instruction}\n\nEmail:\n{email_text}"
    ),
])

_chain_short: Runnable | None = None   # max_tokens=768  for short emails
_chain_long:  Runnable | None = None   # max_tokens=1_500 for long emails


def get_tone_chain(*, long: bool = False) -> Runnable:
    global _chain_short, _chain_long
    if long:
        if _chain_long is None:
            llm = get_groq_llm_large(temperature=0.4, max_tokens=1_500)
            _chain_long = (_prompt | llm | JsonOutputParser()).with_retry(
                stop_after_attempt=3,
            )
        return _chain_long
    else:
        if _chain_short is None:
            llm = get_groq_llm_large(temperature=0.4, max_tokens=768)
            _chain_short = (_prompt | llm | JsonOutputParser()).with_retry(
                stop_after_attempt=3,
            )
        return _chain_short
