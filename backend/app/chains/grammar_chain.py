"""
LCEL chain: grammar, spelling, and style correction.

Uses llama-3.3-70b-versatile for quality.
"""
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.runnables import Runnable

from app.chains.base import get_groq_llm_large

MAX_INPUT_CHARS = 4_000

_SYSTEM = """\
You are a professional copy editor. Identify all grammar, spelling, punctuation, and style \
issues in the given text. Respond with valid JSON only — no prose, no markdown fences.

OUTPUT SCHEMA
{
  "corrected_text": <string — full corrected version of the input>,
  "corrections": [
    {
      "original":    <string — exact phrase as it appears in the input>,
      "corrected":   <string — replacement phrase>,
      "explanation": <string — one short sentence explaining the fix>
    }
  ]
}

RULES
- corrected_text must contain the complete text with all fixes applied.
- corrections must list every individual change made, not summaries.
- If the text has no issues, return an empty corrections array and corrected_text unchanged.
- Do not add, remove, or change meaning — only fix errors.
"""

_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=_SYSTEM),
    HumanMessagePromptTemplate.from_template("{text}"),
])

_chain: Runnable | None = None


def get_grammar_chain() -> Runnable:
    global _chain
    if _chain is None:
        llm = get_groq_llm_large(temperature=0.2, max_tokens=1_024)
        _chain = (_prompt | llm | JsonOutputParser()).with_retry(
            stop_after_attempt=3,
        )
    return _chain
