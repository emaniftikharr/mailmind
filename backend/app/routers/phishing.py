from fastapi import APIRouter, HTTPException

from app.models import PhishingRequest, PhishingResponse
from app.phishing_agent import detect_phishing

router = APIRouter(tags=["phishing"])


@router.post("/phishing", response_model=PhishingResponse)
async def phishing(req: PhishingRequest) -> PhishingResponse:
    try:
        data = await detect_phishing(req.subject, req.body, req.sender)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return PhishingResponse(
        verdict=data["verdict"],
        risk_score=data["risk_score"],
        indicators=data["indicators"],
        explanation=data["explanation"],
        safe_to_open=data["safe_to_open"],
    )
