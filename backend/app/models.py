from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    email_id: str
    subject: str
    body: str
    sender: str | None = None


class AnalyzeResponse(BaseModel):
    email_id: str
    summary: str
    action_items: list[str]
    quick_replies: list[str]
    sentiment: str   # "positive" | "neutral" | "negative"
    tone: str        # "formal" | "informal" | "urgent" | "friendly"
    grammar_issues: list[str]


# Top 5 languages by global business/internet usage
SUPPORTED_LANGUAGES: dict[str, str] = {
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Portuguese": "pt",
    "Japanese": "ja",
}


class Correction(BaseModel):
    original: str
    corrected: str
    explanation: str


class GrammarRequest(BaseModel):
    text: str = Field(min_length=1)


class GrammarResponse(BaseModel):
    corrected_text: str
    corrections: list[Correction]


class TranslateRequest(BaseModel):
    text: str
    target_language: str  # must be a key in SUPPORTED_LANGUAGES


class TranslateResponse(BaseModel):
    translated_text: str
    source_language: str
    target_language: str
