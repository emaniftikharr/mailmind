from fastapi import APIRouter, HTTPException

from app.grammar_agent import check_grammar
from app.models import Correction, GrammarRequest, GrammarResponse

router = APIRouter(tags=["grammar"])


@router.post("/grammar", response_model=GrammarResponse)
async def grammar(req: GrammarRequest) -> GrammarResponse:
    try:
        data = await check_grammar(req.text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    corrections = [
        Correction(
            original=c.get("original", ""),
            corrected=c.get("corrected", ""),
            explanation=c.get("explanation", ""),
        )
        for c in data.get("corrections") or []  # guard: LLM may return null
    ]
    return GrammarResponse(
        corrected_text=data.get("corrected_text", req.text),
        corrections=corrections,
    )
