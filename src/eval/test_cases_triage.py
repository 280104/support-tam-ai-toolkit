"""Test cases for the Task 1 triage eval.

Each case defines a ticket input plus acceptance criteria. Two kinds of
criteria are used:
  - rule_checks: cheap, deterministic assertions on the structured output
    (category/urgency in the right ballpark, KB match grounded, etc.)
  - judge_criteria: a natural-language rubric handed to the LLM-as-judge
    for qualities that can't be checked with a simple rule (tone,
    relevance of the draft reply, reasoning quality).

Cases TC-05 and TC-06 (and the "adversarial" flag) are the deliberately
hard ones: an ambiguous ticket with no clear signal, and a ticket whose
described error has no matching KB doc at all.
"""

TRIAGE_TEST_CASES = [
    {
        "id": "TC-01",
        "adversarial": False,
        "ticket": {
            "ticket_id": "TKT-EVAL-01",
            "subject": "Unable to connect DataBridge Pro to Connectors",
            "body": (
                "Critical issue with DataBridge Pro. Our Connectors pipeline "
                "has been failing since yesterday morning. Error message: "
                "'ERR_CONNECTION_TIMEOUT after 30s'. This is impacting 47 "
                "users in Production. We've tried restarting and clearing "
                "cache but it persists."
            ),
            "plan_tier": "Enterprise",
        },
        "rule_checks": {
            "expected_category": "Bug",
            "expected_urgency_in": ["P1", "P2"],  # production outage, 47 users
            "kb_should_match": True,
        },
        "judge_criteria": (
            "The draft response should acknowledge the specific error "
            "(ERR_CONNECTION_TIMEOUT) and not promise a specific ETA that "
            "wasn't given."
        ),
    },
    {
        "id": "TC-02",
        "adversarial": False,
        "ticket": {
            "ticket_id": "TKT-EVAL-02",
            "subject": "How do I set up SSO with Okta?",
            "body": (
                "We're trying to configure SAML SSO for our Business plan "
                "org using Okta as the IDP. Is there a step-by-step guide?"
            ),
            "plan_tier": "Business",
        },
        "rule_checks": {
            "expected_category": "How-To",
            "expected_urgency_in": ["P3", "P4"],
            "kb_should_match": True,
        },
        "judge_criteria": (
            "The response should point the customer toward SSO/authentication "
            "setup guidance, not treat this as a bug."
        ),
    },
    {
        "id": "TC-03",
        "adversarial": False,
        "ticket": {
            "ticket_id": "TKT-EVAL-03",
            "subject": "Invoice shows wrong seat count",
            "body": (
                "Our latest invoice charges us for 350 seats but we only "
                "have 298 active users. Can someone review our billing?"
            ),
            "plan_tier": "Enterprise",
        },
        "rule_checks": {
            "expected_category": "Billing",
            "expected_urgency_in": ["P2", "P3", "P4"],
            "kb_should_match": True,
        },
        "judge_criteria": (
            "The response should route this to billing, not engineering, "
            "and should not attempt to resolve the billing discrepancy itself."
        ),
    },
    {
        "id": "TC-04",
        "adversarial": False,
        "ticket": {
            "ticket_id": "TKT-EVAL-04",
            "subject": "All our SecureVault secrets disappeared",
            "body": (
                "This morning all secrets in our SecureVault production "
                "vault are showing as empty. This is a total outage for us, "
                "we cannot deploy anything. Need urgent help, this looks "
                "like data loss."
            ),
            "plan_tier": "Enterprise",
        },
        "rule_checks": {
            "expected_category": "Data Loss",
            "expected_urgency_in": ["P1"],
            "kb_should_match": None,  # KB may or may not have this exact scenario
        },
        "judge_criteria": (
            "Given the severity (production outage, apparent data loss), "
            "the urgency and responder team should reflect genuine urgency, "
            "and the response should not sound dismissive."
        ),
    },
    {
        "id": "TC-05-adversarial",
        "adversarial": True,
        "ticket": {
            "ticket_id": "TKT-EVAL-05",
            "subject": "thing broke again",
            "body": "it doesnt work. same as before. pls fix",
            "plan_tier": None,
        },
        "rule_checks": {
            "expected_category": None,  # genuinely ambiguous, no fixed expectation
            "expected_urgency_in": ["P1", "P2", "P3", "P4"],  # any is schema-valid
            "kb_should_match": False,  # too vague to ground in any doc
        },
        "judge_criteria": (
            "Given how little information is in this ticket, the agent "
            "should NOT confidently invent specifics (a specific product, "
            "a confident KB match, a confident urgency justification based "
            "on details not present). The draft response should ask a "
            "clarifying question rather than pretend to understand the issue."
        ),
    },
    {
        "id": "TC-06-adversarial",
        "adversarial": True,
        "ticket": {
            "ticket_id": "TKT-EVAL-06",
            "subject": "Weird flickering in the dashboard widget colors",
            "body": (
                "Not urgent, but our AnalyticsHub dashboard widgets seem to "
                "flicker between two shades of blue when auto-refresh "
                "triggers. Cosmetic only, doesn't affect data. Just curious "
                "if this is a known thing."
            ),
            "plan_tier": "Professional",
        },
        "rule_checks": {
            "expected_category": "Bug",
            "expected_urgency_in": ["P4"],
            "kb_should_match": False,  # not a documented error case
        },
        "judge_criteria": (
            "The agent should correctly recognize this as low-priority/"
            "cosmetic and NOT force a KB match to an unrelated doc just "
            "because AnalyticsHub docs exist."
        ),
    },
]
