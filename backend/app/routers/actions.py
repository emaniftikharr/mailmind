from fastapi import APIRouter, HTTPException

from app.action_agent import extract_actions
from app.models import ActionRequest, ActionResponse

router = APIRouter(tags=["actions"])


@router.post("/actions", response_model=ActionResponse)
async def actions(req: ActionRequest) -> ActionResponse:
    try:
        result = await extract_actions(req.subject, req.body, req.sender)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return ActionResponse(**result)
