from typing import Literal

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


TONE_VARIANTS = ("formal", "friendly", "concise", "persuasive", "executive", "professional")
ToneVariant = Literal["formal", "friendly", "concise", "persuasive", "executive", "professional"]


class ToneRewriteRequest(BaseModel):
    text: str = Field(min_length=1)
    tone: ToneVariant


class ToneRewriteResponse(BaseModel):
    rewritten: str
    tone: str
    changes_summary: str
    truncated: bool = False  # True when input exceeded 2 000 chars and was clipped


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
    text: str = Field(min_length=1)
    target_language: str  # must be a key in SUPPORTED_LANGUAGES


class TranslateResponse(BaseModel):
    translated_text: str
    source_language: str
    target_language: str


class SummarizeRequest(BaseModel):
    text: str


class SummarizeResponse(BaseModel):
    bullets: list[str]
    word_count: int
    was_summarized: bool
