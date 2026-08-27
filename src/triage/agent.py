"""Task 1: Intelligent ticket triage agent.

Callable as a plain Python function (`triage_ticket`) or via the FastAPI
endpoint defined in src/api.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm_client import call_structured  # noqa: E402
from retriever import KnowledgeBaseRetriever  # noqa: E402
from schemas import TriageOutput  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "prompts"))
from triage_prompt import SYSTEM_PROMPT, VERSION, build_user_prompt  # noqa: E402

_retriever: KnowledgeBaseRetriever | None = None


def _get_retriever() -> KnowledgeBaseRetriever:
    global _retriever
    if _retriever is None:
        _retriever = KnowledgeBaseRetriever()
    return _retriever


def triage_ticket(ticket: dict) -> dict:
    """Triage a single ticket.

    Args:
        ticket: dict with at least `subject` and `body`. `ticket_id` and
            `plan_tier` are used if present.

    Returns:
        dict matching schemas.TriageOutput, plus `_prompt_version`.
    """
    retriever = _get_retriever()
    query = f"{ticket.get('subject', '')} {ticket.get('body', '')}"
    kb_excerpts = retriever.search(query, top_k=3)

    user_prompt = build_user_prompt(ticket, kb_excerpts)
    result = call_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=TriageOutput,
        temperature=0.0,
    )

    # Belt-and-suspenders: if the model claimed a KB match, make sure it
    # actually corresponds to a doc we retrieved (never trust the model to
    # only cite what it was given).
    if result["kb_match"]["matched"]:
        retrieved_paths = {e["doc_path"] for e in kb_excerpts}
        if result["kb_match"]["doc_path"] not in retrieved_paths:
            result["kb_match"] = {
                "matched": False,
                "doc_path": None,
                "heading_trail": None,
                "relevance_score": None,
            }

    result["ticket_id"] = ticket.get("ticket_id")
    result["_prompt_version"] = VERSION
    return result


if __name__ == "__main__":
    import json

    sample_ticket = {
        "ticket_id": "TKT-DEMO",
        "subject": "Unable to connect DataBridge Pro to Connectors",
        "body": (
            "We're experiencing a critical issue with DataBridge Pro. Our "
            "Connectors pipeline has been failing since yesterday morning. "
            "Error message: 'ERR_CONNECTION_TIMEOUT after 30s'. This is "
            "impacting 47 users in our Engineering team in Production."
        ),
        "plan_tier": "Enterprise",
    }
    output = triage_ticket(sample_ticket)
    print(json.dumps(output, indent=2))
