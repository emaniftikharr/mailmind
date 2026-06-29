from fastapi import APIRouter, HTTPException

from app.models import SUPPORTED_LANGUAGES, TranslateRequest, TranslateResponse

router = APIRouter(tags=["translate"])


@router.post("/translate", response_model=TranslateResponse)
async def translate(req: TranslateRequest) -> TranslateResponse:
    if req.target_language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported language. Supported: {', '.join(SUPPORTED_LANGUAGES)}",
        )
    # Placeholder — replace with Claude API call
    return TranslateResponse(
        translated_text=f"[{req.target_language} translation placeholder: {req.text[:80]}]",
        source_language="English",
        target_language=req.target_language,
    )
