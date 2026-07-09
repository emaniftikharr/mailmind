from fastapi import APIRouter, HTTPException

from app.models import TONE_VARIANTS, ToneRewriteRequest, ToneRewriteResponse
from app.tone_agent import rewrite_tone

router = APIRouter(tags=["tone"])


@router.post("/rewrite-tone", response_model=ToneRewriteResponse)
async def rewrite(req: ToneRewriteRequest) -> ToneRewriteResponse:
    if req.tone not in TONE_VARIANTS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported tone. Supported: {', '.join(TONE_VARIANTS)}",
        )
    try:
        data = await rewrite_tone(req.text, req.tone)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return ToneRewriteResponse(
        rewritten=data.get("rewritten", req.text),
        tone=req.tone,
        changes_summary=data.get("changes_summary", ""),
        truncated=data.get("truncated", False),
    )
