from fastapi import APIRouter

from app.models import AnalyzeRequest, AnalyzeResponse

router = APIRouter(tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    # Placeholder — replace with Claude API call
    return AnalyzeResponse(
        email_id=req.email_id,
        summary=f'Placeholder summary for "{req.subject}".',
        action_items=[
            "Review the email content",
            "Reply within 24 hours",
        ],
        quick_replies=[
            "Thanks, I'll look into this.",
            "Could you provide more details?",
            "Sounds good, let's proceed.",
        ],
        sentiment="neutral",
        tone="formal",
        grammar_issues=[],
    )
