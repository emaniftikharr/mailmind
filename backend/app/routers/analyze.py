import json

from fastapi import APIRouter, HTTPException

from app.models import AnalyzeRequest, AnalyzeResponse
from app.openai_client import get_client

router = APIRouter(tags=["analyze"])

_SYSTEM = (
    "You are an email analysis assistant. Analyze the provided email and respond "
    "with a JSON object containing exactly these fields:\n"
    '- summary: string (2-3 sentence summary of the email)\n'
    '- action_items: array of strings (specific tasks the recipient should take)\n'
    '- quick_replies: array of exactly 3 short reply strings\n'
    '- sentiment: one of "positive", "neutral", "negative"\n'
    '- tone: one of "formal", "informal", "urgent", "friendly"\n'
    "- grammar_issues: array of strings (grammar/spelling problems; empty if none)"
)


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    user_msg = f"Subject: {req.subject}\nFrom: {req.sender or 'unknown'}\n\n{req.body}"
    try:
        resp = await get_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=512,
            temperature=0.3,
        )
        data = json.loads(resp.choices[0].message.content)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return AnalyzeResponse(
        email_id=req.email_id,
        summary=data.get("summary", ""),
        action_items=data.get("action_items") or [],
        quick_replies=data.get("quick_replies") or [],
        sentiment=data.get("sentiment", "neutral"),
        tone=data.get("tone", "formal"),
        grammar_issues=data.get("grammar_issues", []),
    )
