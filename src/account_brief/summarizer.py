"""Task 2: TAM account health summariser.

Two-stage prompt chain:
  1. Extraction: pull churn/escalation signals, each backed by a direct
     quote from a ticket or escalation note.
  2. Synthesis: turn account data + extracted signals into the final
     3-section brief.

Splitting these into two calls (rather than one big prompt) is a
deliberate reliability choice -- see prompts/account_brief_prompt.py
changelog and the Task 4 design note.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_loader import get_account, get_account_tickets  # noqa: E402
from llm_client import call_structured  # noqa: E402
from schemas import AccountBrief, RiskFlagList  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "prompts"))
from account_brief_prompt import (  # noqa: E402
    EXTRACTION_SYSTEM_PROMPT,
    SYNTHESIS_SYSTEM_PROMPT,
    VERSION,
    build_extraction_prompt,
    build_synthesis_prompt,
)


class AccountNotFoundError(Exception):
    pass


def generate_account_brief(account_id: str) -> dict:
    """Generate a deterministic account health brief for `account_id`.

    Raises AccountNotFoundError if the account_id doesn't exist in
    accounts.json (distinct from "account exists but has no tickets",
    which is a normal, gracefully-handled case).
    """
    account = get_account(account_id)
    if account is None:
        raise AccountNotFoundError(f"No account found for account_id={account_id!r}")

    tickets = get_account_tickets(account_id, days=90)

    # Stage 1: extraction (skip the call entirely if there's nothing to
    # extract from -- saves a request and avoids the model inventing
    # signals from an empty prompt).
    if tickets or account.get("escalation_notes"):
        extraction_result = call_structured(
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            user_prompt=build_extraction_prompt(account, tickets),
            response_model=RiskFlagList,
            temperature=0.0,
        )
        risk_signals = extraction_result["flags"]
    else:
        risk_signals = []

    # Stage 2: synthesis
    brief = call_structured(
        system_prompt=SYNTHESIS_SYSTEM_PROMPT,
        user_prompt=build_synthesis_prompt(account, risk_signals),
        response_model=AccountBrief,
        temperature=0.0,
    )

    brief["account_id"] = account["account_id"]
    brief["company"] = account["company"]
    if not tickets:
        brief["data_completeness_note"] = (
            "No tickets found for this account in the last 90 days "
            "(or in the dataset at all). This brief is based on account "
            "summary data and escalation notes only."
        )
    brief["_prompt_version"] = VERSION
    return brief


if __name__ == "__main__":
    import json

    # ACC-7397 is one of the few accounts in this dataset with an actual
    # linked ticket (see data exploration notes in README) -- good demo case.
    output = generate_account_brief("ACC-7397")
    print(json.dumps(output, indent=2))