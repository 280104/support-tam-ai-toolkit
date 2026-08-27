"""FastAPI app exposing Task 1 (triage) as a REST endpoint.

Run: uvicorn src.api:app --reload
Then: POST http://localhost:8000/triage  with a ticket JSON body.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "triage"))
sys.path.insert(0, str(Path(__file__).resolve().parent / "account_brief"))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from triage.agent import triage_ticket
from account_brief.summarizer import AccountNotFoundError, generate_account_brief

app = FastAPI(
    title="Support & TAM Tooling API",
    description="Task 1 (ticket triage) and Task 2 (account brief) endpoints",
    version="1.0.0",
)


class TicketRequest(BaseModel):
    ticket_id: str | None = None
    subject: str
    body: str
    plan_tier: str | None = None


@app.post("/triage")
def triage(request: TicketRequest) -> dict:
    """Classify a raw support ticket and return a structured triage result."""
    try:
        return triage_ticket(request.model_dump())
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Triage failed: {e}") from e


@app.get("/account-brief/{account_id}")
def account_brief(account_id: str) -> dict:
    """Generate a TAM account health brief for the given account_id."""
    try:
        return generate_account_brief(account_id)
    except AccountNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Brief generation failed: {e}") from e


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
