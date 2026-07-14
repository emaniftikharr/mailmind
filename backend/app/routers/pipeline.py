from fastapi import APIRouter, HTTPException

from app.models import (
    ActionResponse,
    ClassifyResponse,
    LinkAnalysisResponse,
    PhishingResponse,
    PipelineRequest,
    PipelineResponse,
    ReplyResponse,
    TrustResponse,
)
from app.pipeline_agent import run_pipeline

router = APIRouter(tags=["pipeline"])


@router.post("/pipeline", response_model=PipelineResponse)
async def pipeline(req: PipelineRequest) -> PipelineResponse:
    try:
        result = await run_pipeline(req.subject, req.body, req.sender, req.is_html)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return PipelineResponse(
        classification=ClassifyResponse.model_validate(result["classification"]),
        phishing=PhishingResponse.model_validate(result["phishing"]),
        trust=TrustResponse.model_validate(result["trust"]),
        links=LinkAnalysisResponse.model_validate(result["links"]),
        actions=ActionResponse.model_validate(result["actions"]),
        replies=ReplyResponse.model_validate(result["replies"]),
        elapsed_ms=result["elapsed_ms"],
    )
