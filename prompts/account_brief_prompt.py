"""
Prompt: TAM account health brief
Version: v1
Changelog:
  - v1 (2026-08-26): initial version. Two-stage chain: (1) extract raw risk
    signals with direct quotes, (2) synthesize into the final brief. This
    split is what makes the "justify each flag with a direct quote"
    requirement reliable -- asking for extraction and synthesis in one
    shot caused the model to sometimes paraphrase instead of quoting.
  - v1.1 (2026-08-27): extraction now returns an object with a "flags"
    array instead of a top-level JSON array -- a top-level array as the
    LLM response schema was observed to lose field-level "required"
    information, causing the model to omit signal/quote/severity.
"""

VERSION = "v1"

# Stage 1: extract candidate risk signals as directly-quoted evidence.
EXTRACTION_SYSTEM_PROMPT = """You extract churn-risk and escalation signals \
from account data and support tickets for a Technical Account Manager (TAM).

Rules:
- Every signal you report MUST include a direct quote copied verbatim from \
the ticket body or an escalation note. Do not paraphrase the quote field.
- If there are no real risk signals, return an empty "flags" list rather \
than inventing one.
- Respond ONLY with valid JSON: an object with a "flags" field containing \
a list of objects, each with {ticket_id_or_null, signal, justification_quote, severity}.
"""

# Stage 2: synthesize into the final structured brief.
SYNTHESIS_SYSTEM_PROMPT = """You are a TAM account health briefing assistant. \
You are given structured account data and a pre-extracted list of risk \
signals (already quote-justified). Produce a concise account brief a TAM \
can read in under a minute before a QBR.

Rules:
- executive_summary: 3-5 sentences, factual, no fluff.
- risks_and_flags: use the pre-extracted signals as-is (do not invent new \
ones, do not drop the justification_quote).
- recommended_talking_points: 3-5 short, concrete, actionable bullets for \
the TAM to raise with the customer.
- If there is no recent ticket data for this account, set \
data_completeness_note explaining that the brief is based on account \
summary data only, and keep claims conservative accordingly.
- Respond ONLY with valid JSON matching the provided schema.
"""


def build_extraction_prompt(account: dict, tickets: list[dict]) -> str:
    ticket_block = "\n\n".join(
        f"[Ticket {t['ticket_id']}] status={t['status']} urgency={t['urgency']} "
        f"category={t['category']}\nsubject: {t['subject']}\nbody: {t['body']}"
        for t in tickets
    ) or "(no tickets found for this account in the lookback window)"

    notes_block = "\n".join(f"- {n}" for n in account.get("escalation_notes", [])) or "(none)"

    return f"""ACCOUNT: {account['company']} ({account['account_id']})
health_status: {account.get('health_status')}
usage_trend: {account.get('usage_trend')}
p1_tickets_last_30d: {account.get('p1_tickets_last_30d')}
nps_score: {account.get('nps_score')}
last_login_days_ago: {account.get('last_login_days_ago')}

ESCALATION NOTES
{notes_block}

RECENT TICKETS (last 90 days)
{ticket_block}

Extract all churn-risk / escalation signals as instructed."""


def build_synthesis_prompt(account: dict, risk_signals: list[dict]) -> str:
    return f"""ACCOUNT DATA
{account}

PRE-EXTRACTED RISK SIGNALS (use as-is, do not invent new ones)
{risk_signals}

Produce the final structured account brief."""