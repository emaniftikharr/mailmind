from fastapi import APIRouter, HTTPException

from app.flowchart_agent import detect_flowchart
from app.models import FlowchartRequest, FlowchartResponse

router = APIRouter(tags=["flowchart"])


@router.post("/flowchart", response_model=FlowchartResponse)
async def flowchart(req: FlowchartRequest) -> FlowchartResponse:
    try:
        result = await detect_flowchart(req.subject, req.body)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return FlowchartResponse.model_validate(result)
