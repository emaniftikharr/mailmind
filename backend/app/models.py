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


PriorityLevel = Literal["urgent", "high", "normal", "low"]


class ClassifyRequest(BaseModel):
    subject: str = Field(default="")
    body: str = Field(min_length=1)


class ClassifyResponse(BaseModel):
    category: str
    priority: PriorityLevel
    confidence: float
    reason: str
    all_categories: list[str]
    all_priorities: list[str]


PhishingVerdict = Literal["phishing", "suspicious", "legitimate"]


class PhishingRequest(BaseModel):
    subject: str = Field(default="")
    body: str = Field(min_length=1)
    sender: str = Field(default="")


class PhishingResponse(BaseModel):
    verdict: PhishingVerdict
    risk_score: float          # 0.0 – 1.0
    indicators: list[str]      # subset of the 10 indicator keys
    explanation: str
    safe_to_open: bool


class LinkInfoModel(BaseModel):
    url: str
    display_text: str
    domain: str
    display_domain: str
    is_shortened: bool
    risk_flags: list[str]


class LinkAnalysisRequest(BaseModel):
    subject: str = Field(default="")
    body: str = Field(min_length=1)
    is_html: bool = False


class LinkAnalysisResponse(BaseModel):
    links: list[LinkInfoModel]
    total: int
    flagged: int
    risk_flags: list[str]


class UrgencyHitModel(BaseModel):
    category: str
    matched_text: str


class CredentialHitModel(BaseModel):
    category: str
    matched_text: str


class TrustRequest(BaseModel):
    subject: str = Field(default="")
    body: str = Field(min_length=1)
    is_html: bool = False
    link_flags: list[str] = Field(default_factory=list)  # pre-computed; omit to auto-extract


class TrustResponse(BaseModel):
    trust_score: int                          # 0–100
    risk_level: str                           # "low" | "moderate" | "high" | "critical"
    urgency_hits: list[UrgencyHitModel]
    urgency_categories: list[str]
    credential_hits: list[CredentialHitModel]
    credential_categories: list[str]
    link_flags: list[str]
    score_breakdown: dict[str, int]
    summary: str


class DeadlineModel(BaseModel):
    phrase: str
    resolved_date: str | None       # ISO 8601 or None for ASAP
    confidence: str                 # "high" | "medium" | "low"
    is_relative: bool
    urgency: str                    # "today" | "tomorrow" | "this_week" | "next_week" | "this_month" | "future" | "asap" | "overdue"


class MeetingModel(BaseModel):
    meeting_detected: bool
    title: str
    date_str: str                   # raw text from email
    time_str: str
    duration_minutes: int | None
    location: str
    organizer: str
    attendees: list[str]
    agenda: str
    is_tentative: bool
    extraction_error: str | None    # set on LLM failure


class TaskModel(BaseModel):
    title: str
    description: str
    assignee: str           # "me" | "them" | "other"
    due_date_str: str       # raw text from email
    priority: str           # "urgent" | "high" | "normal" | "low"


class ActionRequest(BaseModel):
    subject: str = Field(default="")
    body: str = Field(min_length=1)
    sender: str = Field(default="")


class ReplyVariant(BaseModel):
    label: str           # intent label, e.g. "Accept", "Decline"
    tone: str            # "formal" | "friendly" | "direct"
    text: str            # complete ready-to-send reply body


class ReplyRequest(BaseModel):
    subject: str = Field(default="")
    body: str = Field(min_length=1)
    sender: str = Field(default="")
    category: str = Field(default="")      # from classification, e.g. "meeting"
    priority: str = Field(default="normal") # from classification


class ReplyResponse(BaseModel):
    variants: list[ReplyVariant]
    count: int
    reply_needed: bool = True  # False for automated notifications / newsletters


class ActionResponse(BaseModel):
    meeting: MeetingModel
    deadlines: list[DeadlineModel]
    tasks: list[TaskModel]
    has_meeting: bool
    has_deadlines: bool
    has_tasks: bool


FlowchartNodeType = Literal["start", "end", "step", "decision"]
FlowchartType = Literal["sequential", "branching", "parallel"]


class FlowchartNode(BaseModel):
    id: str
    label: str
    type: FlowchartNodeType
    description: str = ""


class FlowchartEdge(BaseModel):
    source: str
    target: str
    label: str = ""


class FlowchartRequest(BaseModel):
    subject: str = Field(default="")
    body: str = Field(min_length=1)


class FlowchartResponse(BaseModel):
    has_flowchart: bool
    title: str = ""
    flowchart_type: FlowchartType | None = None
    nodes: list[FlowchartNode] = []
    edges: list[FlowchartEdge] = []
    mermaid: str = ""


class PipelineRequest(BaseModel):
    subject: str = Field(default="")
    body: str = Field(min_length=1)
    sender: str = Field(default="")
    is_html: bool = False


class PipelineResponse(BaseModel):
    classification: ClassifyResponse
    phishing: PhishingResponse
    trust: TrustResponse
    links: LinkAnalysisResponse
    actions: ActionResponse
    replies: ReplyResponse
    elapsed_ms: int
