from app.chains.grammar_chain import MAX_INPUT_CHARS, get_grammar_chain


async def check_grammar(text: str) -> dict:
    return await get_grammar_chain().ainvoke({"text": text[:MAX_INPUT_CHARS]})
