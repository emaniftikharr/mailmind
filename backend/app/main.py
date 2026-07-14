import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import actions, analyze, classify, flowchart, grammar, health, links, phishing, pipeline, replies, summarize, tone, translate, trust

load_dotenv()

app = FastAPI(title="MailMind API", version="0.1.0")

# Content scripts run in the Gmail page context, so mail.google.com is the
# effective origin. Background service workers and the popup use the
# extension's own chrome-extension:// origin.
_extension_id = os.getenv("CHROME_EXTENSION_ID", "")

_origins: list[str] = [
    "https://mail.google.com",
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:8000",
]

if _extension_id:
    _origins.append(f"chrome-extension://{_extension_id}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(health.router)
app.include_router(analyze.router, prefix="/api/v1")
app.include_router(classify.router, prefix="/api/v1")
app.include_router(links.router, prefix="/api/v1")
app.include_router(phishing.router, prefix="/api/v1")
app.include_router(grammar.router, prefix="/api/v1")
app.include_router(summarize.router, prefix="/api/v1")
app.include_router(tone.router, prefix="/api/v1")
app.include_router(translate.router, prefix="/api/v1")
app.include_router(trust.router, prefix="/api/v1")
app.include_router(actions.router, prefix="/api/v1")
app.include_router(replies.router, prefix="/api/v1")
app.include_router(pipeline.router, prefix="/api/v1")
app.include_router(flowchart.router, prefix="/api/v1")
