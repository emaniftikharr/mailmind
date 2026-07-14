import os

from langchain_openai import ChatOpenAI

# Fast model: 500k TPD — used for classification, meeting/task extraction, replies
_DEFAULT_MODEL = "llama-3.1-8b-instant"

# Quality model: 100k TPD — used for summarisation, grammar, tone rewrite, translation
_LARGE_MODEL = "llama-3.3-70b-versatile"

# Cache keyed by (model, temperature, max_tokens) so multiple agents can safely
# coexist without overwriting each other's LLM instances.
_llms: dict[tuple, ChatOpenAI] = {}


def get_groq_llm(
    *,
    temperature: float = 0.1,
    max_tokens: int = 256,
    model: str | None = None,
) -> ChatOpenAI:
    """Return a cached ChatOpenAI pointed at the Groq endpoint.

    Each unique (model, temperature, max_tokens) triple gets its own instance.
    Pass model=_LARGE_MODEL for quality-critical tasks that need 70b.
    """
    resolved = model or os.getenv("GROQ_MODEL", _DEFAULT_MODEL)
    key = (resolved, temperature, max_tokens)
    if key not in _llms:
        api_key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY environment variable is not set")
        _llms[key] = ChatOpenAI(
            model=resolved,
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
            temperature=temperature,
            max_tokens=max_tokens,
            model_kwargs={"response_format": {"type": "json_object"}},
        )
    return _llms[key]


def get_groq_llm_large(*, temperature: float = 0.1, max_tokens: int = 512) -> ChatOpenAI:
    """Convenience wrapper for the 70b quality model."""
    return get_groq_llm(temperature=temperature, max_tokens=max_tokens, model=_LARGE_MODEL)
