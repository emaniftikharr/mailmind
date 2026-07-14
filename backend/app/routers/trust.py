from fastapi import APIRouter, HTTPException

from app.link_analyzer import analyze_email_links
from app.models import (
    CredentialHitModel,
    TrustRequest,
    TrustResponse,
    UrgencyHitModel,
)
from app.social_engineering import analyze_trust

router = APIRouter(tags=["trust"])


@router.post("/trust", response_model=TrustResponse)
def trust(req: TrustRequest) -> TrustResponse:
    try:
        # Resolve link flags: use caller-supplied flags or extract from body
        if req.link_flags:
            link_flags = req.link_flags
        else:
            link_data = analyze_email_links(req.body, subject=req.subject, is_html=req.is_html)
            link_flags = link_data["risk_flags"]

        report = analyze_trust(req.subject, req.body, link_flags=link_flags)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return TrustResponse(
        trust_score=report.trust_score,
        risk_level=report.risk_level,
        urgency_hits=[
            UrgencyHitModel(category=h.category, matched_text=h.matched_text)
            for h in report.urgency_hits
        ],
        urgency_categories=report.urgency_categories,
        credential_hits=[
            CredentialHitModel(category=h.category, matched_text=h.matched_text)
            for h in report.credential_hits
        ],
        credential_categories=report.credential_categories,
        link_flags=report.link_flags,
        score_breakdown=report.score_breakdown,
        summary=report.summary,
    )
