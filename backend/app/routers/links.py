from fastapi import APIRouter, HTTPException

from app.link_analyzer import analyze_email_links
from app.models import LinkAnalysisRequest, LinkAnalysisResponse

router = APIRouter(tags=["links"])


@router.post("/links", response_model=LinkAnalysisResponse)
def links(req: LinkAnalysisRequest) -> LinkAnalysisResponse:
    try:
        data = analyze_email_links(req.body, subject=req.subject, is_html=req.is_html)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return LinkAnalysisResponse(
        links=data["links"],
        total=data["total"],
        flagged=data["flagged"],
        risk_flags=data["risk_flags"],
    )
