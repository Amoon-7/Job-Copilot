from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .. import services
from ..db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Job Copilot", version="0.1.0", lifespan=lifespan)


class ReviewIn(BaseModel):
    action: Literal["approve", "edit", "reject"]
    edited_content: dict | None = None
    reason: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest")
def ingest():
    return services.ingest_all()


@app.post("/match")
def match(top_k: int = 10):
    try:
        return services.run_matching(top_k)
    except FileNotFoundError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/matches")
def matches(limit: int = 20):
    return services.list_matches(limit)


@app.post("/offers/{offer_id}/draft")
def draft(offer_id: int):
    try:
        return services.generate_draft(offer_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/drafts")
def drafts(status: str | None = "pending"):
    return services.list_drafts(status)


@app.post("/drafts/{draft_id}/review")
def review(draft_id: int, body: ReviewIn):
    try:
        return services.review_draft(draft_id, body.action, body.edited_content, body.reason)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
