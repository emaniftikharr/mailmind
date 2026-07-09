from fastapi import APIRouter, HTTPException

from app.models import SUPPORTED_LANGUAGES, TranslateRequest, TranslateResponse
from app.translate_agent import translate_text

router = APIRouter(tags=["translate"])


@router.post("/translate", response_model=TranslateResponse)
async def translate(req: TranslateRequest) -> TranslateResponse:
    if req.target_language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported language. Supported: {', '.join(SUPPORTED_LANGUAGES)}",
        )
    try:
        data = await translate_text(req.text, req.target_language)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return TranslateResponse(
        translated_text=data.get("translated_text", ""),
        source_language=data.get("source_language", "English"),
        target_language=req.target_language,
    )
