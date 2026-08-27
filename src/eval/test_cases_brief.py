"""Test cases for the Task 2 account brief eval.

BC-05 is the adversarial case: an account_id that doesn't exist at all
(not "exists with no tickets" -- genuinely absent), which should raise
AccountNotFoundError rather than silently fabricating a brief.
"""

BRIEF_TEST_CASES = [
    {
        "id": "BC-01",
        "adversarial": False,
        "account_id": "ACC-7397",  # Gavin Belson Co: At Risk, has a linked ticket
        "rule_checks": {
            "should_succeed": True,
            "min_talking_points": 1,
            "risk_flags_require_quotes": True,
        },
        "judge_criteria": (
            "Given this account is flagged 'At Risk' with negative-sentiment "
            "and repeated-P1 escalation notes, the executive summary should "
            "reflect that risk rather than reading as a routine healthy-account "
            "summary."
        ),
    },
    {
        "id": "BC-02",
        "adversarial": False,
        "account_id": "ACC-5748",  # Nexus Data: New, no escalation notes
        "rule_checks": {
            "should_succeed": True,
            "min_talking_points": 1,
            "risk_flags_require_quotes": True,
        },
        "judge_criteria": (
            "Given this is a 'New' account with no escalation notes, the "
            "brief should not invent churn risk that isn't supported by data."
        ),
    },
    {
        "id": "BC-03",
        "adversarial": False,
        # Any account_id with zero linked tickets (the common case in this
        # dataset) -- picked at eval-run time to always be a valid account
        # with an empty ticket list, see harness.py.
        "account_id": None,
        "rule_checks": {
            "should_succeed": True,
            "requires_data_completeness_note": True,
        },
        "judge_criteria": (
            "With no ticket history available, the brief should be "
            "appropriately conservative and explicitly note the data gap, "
            "not fabricate specific ticket-based claims."
        ),
    },
    {
        "id": "BC-04",
        "adversarial": False,
        "account_id": "ACC-1785",  # Cyberdyne Systems: At Risk
        "rule_checks": {
            "should_succeed": True,
            "min_talking_points": 1,
            "risk_flags_require_quotes": True,
        },
        "judge_criteria": (
            "The brief should surface the procurement/pricing-review signal "
            "as a talking point, since that's a concrete, actionable risk."
        ),
    },
    {
        "id": "BC-05-adversarial",
        "adversarial": True,
        "account_id": "ACC-99999-DOES-NOT-EXIST",
        "rule_checks": {
            "should_succeed": False,  # must raise AccountNotFoundError
        },
        "judge_criteria": None,
    },
]
