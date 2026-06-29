from pydantic import BaseModel


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
    sentiment: str  # "positive" | "neutral" | "negative"
