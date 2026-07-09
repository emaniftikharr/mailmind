from fastapi import APIRouter, HTTPException

from app.models import SummarizeRequest, SummarizeResponse
from app.summary_agent import summarize_email

router = APIRouter(tags=["summarize"])


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize(req: SummarizeRequest) -> SummarizeResponse:
    try:
        data = await summarize_email(req.text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return SummarizeResponse(
        bullets=data.get("bullets", []),
        word_count=data.get("word_count", 0),
        was_summarized=data.get("was_summarized", False),
    )
