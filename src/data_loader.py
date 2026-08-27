"""
Loads tickets.json / accounts.json and provides join helpers.

Per README.md / DATA_SCHEMA.md:
  - Not every ticket.account_id has a matching account record. Handle
    missing lookups gracefully (return None, don't raise).
  - Account health analysis should use the last 90 days of tickets.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"


@lru_cache(maxsize=1)
def load_tickets() -> list[dict]:
    return json.loads((DATA_ROOT / "tickets.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_accounts() -> list[dict]:
    return json.loads((DATA_ROOT / "accounts.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _account_map() -> dict[str, dict]:
    return {a["account_id"]: a for a in load_accounts()}


def get_account(account_id: str) -> dict | None:
    """Return the account record, or None if it doesn't exist.

    Ticket account_ids don't always resolve to a real account (intentional
    data gap per the starter README) — callers must handle None.
    """
    return _account_map().get(account_id)


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def get_account_tickets(account_id: str, days: int = 90) -> list[dict]:
    """Tickets for an account within the last `days`, newest first.

    Note: the dataset's created_at values are historical (2025), so "last
    90 days" is computed relative to the most recent ticket timestamp in
    the dataset, not wall-clock `now()` — otherwise every account would
    return zero tickets. This keeps the tool usable against a static
    snapshot dataset, which is the realistic production scenario (a
    nightly ETL snapshot, not a live clock).
    """
    all_tickets = [t for t in load_tickets() if t["account_id"] == account_id]
    if not all_tickets:
        return []

    most_recent = max(_parse_ts(t["created_at"]) for t in all_tickets)
    cutoff = most_recent - timedelta(days=days)

    recent = [t for t in all_tickets if _parse_ts(t["created_at"]) > cutoff]
    recent.sort(key=lambda t: t["created_at"], reverse=True)
    return recent


def account_exists(account_id: str) -> bool:
    return account_id in _account_map()


if __name__ == "__main__":
    tickets = load_tickets()
    accounts = load_accounts()
    print(f"{len(tickets)} tickets, {len(accounts)} accounts loaded")

    orphans = [t for t in tickets if not account_exists(t["account_id"])]
    print(f"{len(orphans)} tickets reference an account_id with no account record")

    sample_id = accounts[0]["account_id"]
    recent = get_account_tickets(sample_id)
    print(f"Account {sample_id}: {len(recent)} tickets in trailing 90d window")
