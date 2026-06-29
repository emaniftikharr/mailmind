import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import analyze, health

load_dotenv()

app = FastAPI(title="MailMind API", version="0.1.0")

# Build allowed origins list.
# Content scripts run in the Gmail page context, so gmail.google.com is needed.
# Background service workers and the popup use the extension's own origin.
_extension_id = os.getenv("CHROME_EXTENSION_ID", "")

_origins: list[str] = [
    "https://mail.google.com",   # content script origin
    "http://localhost:5173",     # Vite dev server
    "http://localhost:3000",
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
