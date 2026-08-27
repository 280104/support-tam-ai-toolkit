# Design Note

## Failure modes

**1. Silent misclassification on ambiguous or low-signal tickets.**
Ticket TC-05 in the eval set ("thing broke again, same as before, pls fix")
has almost no real signal, yet the schema forces the model to output a
concrete category and urgency anyway — there's no "I don't know" option in
a structured schema. The risk is a ticket getting confidently routed to the
wrong team or wrong priority with a plausible-sounding justification.
*Detection:* the eval harness's LLM-as-judge specifically checks whether
the model invents specifics not present in the ticket (see TC-05/TC-06).
*Mitigation:* add a `confidence` field to `TriageOutput` and route
low-confidence tickets to a human-review queue instead of auto-assigning,
rather than trying to eliminate ambiguity from the classifier itself.

**2. Knowledge-base grounding drift (the model citing a doc it wasn't
actually given).** LLMs will sometimes reference a plausible-sounding KB
doc even when retrieval didn't surface it, especially when the true answer
isn't in the KB at all. *Detection:* the triage agent already
cross-checks the model's claimed `doc_path` against the actual retrieved
chunk set post-hoc (see `triage/agent.py`) and force-clears the match if
it doesn't correspond to a real retrieved chunk. *Mitigation:* this check
already exists in code, not just as a hope; a production version would
also log every discarded false-match for retrieval-quality monitoring.

**3. Data/reality drift between structured fields and raw records.**
Exploring the dataset surfaced a concrete example: account `ACC-7397`
reports `open_tickets: 9` in its summary record, but only 1 ticket in
`tickets.json` actually links to that `account_id`. A summarizer that
trusts the structured `open_tickets` field over the actual ticket log will
overstate account risk. *Detection:* a consistency-check eval case
comparing `account.open_tickets` against `len(get_account_tickets())`.
*Mitigation:* the brief already treats the linked-ticket log as the source
of truth for specific claims (with direct quotes required), and only uses
account-level fields for high-level framing — deliberately not letting
`open_tickets` drive a specific numeric claim it can't back up.

## Latency vs. quality trade-off

Task 2 uses a two-stage prompt chain (extract risk signals with quotes,
then synthesize the brief) instead of one combined prompt. This roughly
doubles latency and API calls for that endpoint. The trade-off was made
because a single-prompt version was unreliable at satisfying "justify each
flag with a direct quote" — the model would paraphrase instead of quoting
verbatim when asked to extract and synthesize in the same pass. Splitting
the steps made quote-fidelity close to deterministic-set-driven.
*If latency were the hard constraint:* collapse back to one prompt, but
mechanically enforce quote-fidelity in code — search each claimed
`justification_quote` as a literal substring of the source ticket/note
text, and drop or flag any flag whose quote doesn't verify. That trades a
second LLM call for a much cheaper string-matching validation pass.

## Data sensitivity

Ticket bodies and account escalation notes could contain PII (names,
emails, internal system details) in a real deployment, even though this
mock dataset is synthetic. Three things bound the design accordingly: (1)
`llm_client.py` is the single chokepoint for all outbound model calls —
that's deliberate, so a PII-redaction step can be inserted in exactly one
place later without touching Task 1/2/3 logic. (2) No data is persisted
by this tool beyond the request/response cycle; nothing is logged to a
third party. (3) The retrieval layer runs entirely locally (TF-IDF, no
embedding API), so knowledge-base content never leaves the process, only
the ticket/account text sent to the LLM does, and that's the minimum
necessary content, not a bulk data dump.

## Scaling to 10× ticket volume

At 5,000 tickets/day instead of 500, the first thing to break is almost
certainly **the free-tier LLM rate limit**, not the code — the harness
already inserts a 1-second delay between eval calls specifically because
of this. The TF-IDF retriever would still scale fine (cosine similarity
over a few thousand rows is trivial), but the KB corpus itself would need
periodic rebuilding if docs are updated frequently, since the vectorizer
is fit once at process start. The account-brief tool's `lru_cache`d data
loaders would also need a real refresh strategy instead of process-lifetime
caching, since account data isn't static in production. The practical
next step at that volume is a request queue in front of the LLM calls
with backoff, plus moving off the free tier to a rate-limited paid tier
with predictable throughput.
