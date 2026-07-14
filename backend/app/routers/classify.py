from fastapi import APIRouter, HTTPException

from app.classification_agent import classify_email
from app.models import ClassifyRequest, ClassifyResponse

router = APIRouter(tags=["classify"])


@router.post("/classify", response_model=ClassifyResponse)
async def classify(req: ClassifyRequest) -> ClassifyResponse:
    try:
        data = await classify_email(req.subject, req.body)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return ClassifyResponse(
        category=data["category"],
        priority=data["priority"],
        confidence=data["confidence"],
        reason=data["reason"],
        all_categories=data["all_categories"],
        all_priorities=data["all_priorities"],
    )
