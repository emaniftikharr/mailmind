from fastapi import APIRouter, HTTPException

from app.models import ReplyRequest, ReplyResponse
from app.reply_agent import generate_replies

router = APIRouter(tags=["replies"])


@router.post("/replies", response_model=ReplyResponse)
async def replies(req: ReplyRequest) -> ReplyResponse:
    try:
        result = await generate_replies(
            req.subject, req.body, req.sender, req.category, req.priority
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return ReplyResponse(**result)
