"""Structured output schemas shared by Task 1 (triage) and Task 2 (brief)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# --- Task 1: Ticket Triage -------------------------------------------------

Urgency = Literal["P1", "P2", "P3", "P4"]

Category = Literal[
    "Bug",
    "Feature Request",
    "How-To",
    "Performance",
    "Billing",
    "Integration",
    "Onboarding",
    "Data Loss",
]

ResponderTeam = Literal[
    "Tier-1 Support",
    "Tier-2 Engineering",
    "Billing Team",
    "Onboarding Specialist",
    "Security/SecureVault Team",
    "Product/Feature Requests",
]


class KBMatch(BaseModel):
    matched: bool = Field(description="Whether a relevant KB doc was found")
    doc_path: str | None = Field(
        description="Relative path of the matched KB doc, or null if no match"
    )
    heading_trail: str | None = Field(
        description="Section heading trail within the doc, or null if no match"
    )
    relevance_score: float | None = Field(
        description="Retrieval similarity score (0-1), or null if no match"
    )


class TriageOutput(BaseModel):
    ticket_id: str | None = Field(description="Ticket ID if known, else null")
    product_area: str = Field(description="Product and/or module the ticket relates to")
    category: Category
    urgency: Urgency
    urgency_reasoning: str = Field(
        description="1-2 sentence justification for the assigned urgency tier"
    )
    kb_match: KBMatch
    recommended_responder_team: ResponderTeam
    draft_first_response: str = Field(
        description="Draft reply message a support agent could send/edit"
    )


# --- Task 2: TAM Account Health Brief --------------------------------------

class RiskFlag(BaseModel):
    ticket_id: str | None = Field(
        description="Ticket this flag is derived from, or null if not applicable"
    )
    signal: str = Field(description="Short label for the risk/churn signal")
    justification_quote: str = Field(
        description="Direct quote from the ticket or escalation note supporting this flag"
    )
    severity: Literal["low", "medium", "high"]


class RiskFlagList(BaseModel):
    """Wrapper object so the LLM response schema is a JSON object, not a
    top-level JSON array. Passing list[RiskFlag] directly as the response
    schema was observed to lose field-level 'required' information in
    practice (the model would return items missing signal/quote/severity
    even though they have no default value) -- wrapping in an object with
    a single array field avoids that."""
    flags: list[RiskFlag] = Field(description="Extracted risk/churn signals")

class AccountBrief(BaseModel):
    account_id: str
    company: str
    executive_summary: str = Field(description="3-5 sentence executive summary")
    risks_and_flags: list[RiskFlag]
    recommended_talking_points: list[str]
    data_completeness_note: str | None = Field(
        description="Note on any data gaps that limited this brief (e.g. no "
        "tickets found for this account in the lookback window), or null if none"
    )
