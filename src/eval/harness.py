"""Task 3: Evaluation harness for Task 1 (triage) and Task 2 (account brief).

Scoring approach per test case:
  - rule_score (0 or 1): deterministic checks against the structured output
    (schema-level facts: category/urgency in range, KB match grounding,
    required fields present).
  - judge_score (0-1): LLM-as-judge rates how well the output satisfies a
    natural-language rubric that can't be checked mechanically (tone,
    reasoning quality, whether the model overreached on a vague ticket).
  - final quality_score = average of the two that were applicable.

Run: python -m src.eval.harness   (from repo root, with GEMINI_API_KEY set)
Produces: eval_report.json and eval_report.md in the repo root.
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "triage"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "account_brief"))

from data_loader import load_accounts, load_tickets  # noqa: E402
from llm_client import call_structured  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from triage.agent import triage_ticket  # noqa: E402
from account_brief.summarizer import AccountNotFoundError, generate_account_brief  # noqa: E402

from test_cases_triage import TRIAGE_TEST_CASES  # noqa: E402
from test_cases_brief import BRIEF_TEST_CASES  # noqa: E402


class JudgeVerdict(BaseModel):
    score: float = Field(description="0.0 (fails rubric) to 1.0 (fully satisfies rubric)")
    rationale: str = Field(description="1-2 sentence explanation of the score")


JUDGE_SYSTEM_PROMPT = """You are a strict QA evaluator for an AI support/TAM \
tool. You are given an input, the tool's structured output, and a rubric. \
Score how well the output satisfies the rubric from 0.0 to 1.0. Be a harsh, \
literal grader -- do not give credit for effort, only for actually meeting \
the rubric. Respond only with valid JSON: {"score": <float>, "rationale": <string>}.
"""


def _judge(input_desc: str, output_desc: str, rubric: str) -> dict:
    prompt = f"INPUT:\n{input_desc}\n\nOUTPUT:\n{output_desc}\n\nRUBRIC:\n{rubric}"
    return call_structured(
        system_prompt=JUDGE_SYSTEM_PROMPT,
        user_prompt=prompt,
        response_model=JudgeVerdict,
        temperature=0.0,
    )


# --- Task 1 eval -------------------------------------------------------

def run_triage_case(case: dict) -> dict:
    result = {"id": case["id"], "adversarial": case["adversarial"]}
    try:
        output = triage_ticket(case["ticket"])
    except Exception as e:  # noqa: BLE001
        result.update(passed=False, quality_score=0.0, error=str(e))
        return result

    rule_checks = case["rule_checks"]
    rule_failures = []

    exp_cat = rule_checks.get("expected_category")
    if exp_cat is not None and output.get("category") != exp_cat:
        rule_failures.append(f"expected category={exp_cat}, got {output.get('category')}")

    exp_urg = rule_checks.get("expected_urgency_in")
    if exp_urg is not None and output.get("urgency") not in exp_urg:
        rule_failures.append(f"expected urgency in {exp_urg}, got {output.get('urgency')}")

    exp_kb = rule_checks.get("kb_should_match")
    if exp_kb is not None:
        actual_matched = output.get("kb_match", {}).get("matched")
        if actual_matched != exp_kb:
            rule_failures.append(f"expected kb_match.matched={exp_kb}, got {actual_matched}")

    rule_score = 0.0 if rule_failures else 1.0

    judge_score = None
    judge_rationale = None
    if case.get("judge_criteria"):
        try:
            verdict = _judge(
                input_desc=json.dumps(case["ticket"]),
                output_desc=json.dumps(output),
                rubric=case["judge_criteria"],
            )
            judge_score = verdict["score"]
            judge_rationale = verdict["rationale"]
        except Exception as e:  # noqa: BLE001
            judge_rationale = f"judge call failed: {e}"

    scores = [s for s in [rule_score, judge_score] if s is not None]
    quality_score = sum(scores) / len(scores) if scores else 0.0

    result.update(
        passed=quality_score >= 0.5,
        quality_score=round(quality_score, 3),
        rule_score=rule_score,
        rule_failures=rule_failures,
        judge_score=judge_score,
        judge_rationale=judge_rationale,
        output=output,
    )
    return result


# --- Task 2 eval -------------------------------------------------------

def _pick_zero_ticket_account() -> str:
    """Find an account_id in accounts.json with no linked tickets, for BC-03."""
    tickets = load_tickets()
    linked = {t["account_id"] for t in tickets}
    accounts = load_accounts()
    for a in accounts:
        if a["account_id"] not in linked:
            return a["account_id"]
    raise RuntimeError("Could not find an account with zero linked tickets")


def run_brief_case(case: dict) -> dict:
    result = {"id": case["id"], "adversarial": case["adversarial"]}
    account_id = case["account_id"] or _pick_zero_ticket_account()
    rule_checks = case["rule_checks"]

    try:
        output = generate_account_brief(account_id)
    except AccountNotFoundError as e:
        if rule_checks.get("should_succeed") is False:
            result.update(passed=True, quality_score=1.0, rule_score=1.0,
                           rule_failures=[], note=f"correctly raised: {e}")
        else:
            result.update(passed=False, quality_score=0.0, error=str(e))
        return result
    except Exception as e:  # noqa: BLE001
        result.update(passed=False, quality_score=0.0, error=str(e))
        return result

    if rule_checks.get("should_succeed") is False:
        result.update(
            passed=False, quality_score=0.0,
            error="expected AccountNotFoundError but call succeeded",
        )
        return result

    rule_failures = []
    min_tp = rule_checks.get("min_talking_points")
    if min_tp is not None and len(output.get("recommended_talking_points", [])) < min_tp:
        rule_failures.append("too few recommended_talking_points")

    if rule_checks.get("risk_flags_require_quotes"):
        for flag in output.get("risks_and_flags", []):
            if not flag.get("justification_quote", "").strip():
                rule_failures.append(f"risk flag missing quote: {flag.get('signal')}")

    if rule_checks.get("requires_data_completeness_note"):
        if not output.get("data_completeness_note"):
            rule_failures.append("expected data_completeness_note to be set")

    rule_score = 0.0 if rule_failures else 1.0

    judge_score = None
    judge_rationale = None
    if case.get("judge_criteria"):
        try:
            verdict = _judge(
                input_desc=f"account_id={account_id}",
                output_desc=json.dumps(output),
                rubric=case["judge_criteria"],
            )
            judge_score = verdict["score"]
            judge_rationale = verdict["rationale"]
        except Exception as e:  # noqa: BLE001
            judge_rationale = f"judge call failed: {e}"

    scores = [s for s in [rule_score, judge_score] if s is not None]
    quality_score = sum(scores) / len(scores) if scores else 0.0

    result.update(
        passed=quality_score >= 0.5,
        quality_score=round(quality_score, 3),
        rule_score=rule_score,
        rule_failures=rule_failures,
        judge_score=judge_score,
        judge_rationale=judge_rationale,
        output=output,
    )
    return result


# --- Report generation ---------------------------------------------------

def run_all() -> dict:
    triage_results = []
    for case in TRIAGE_TEST_CASES:
        try:
            triage_results.append(run_triage_case(case))
        except Exception as e:  # noqa: BLE001
            triage_results.append({
                "id": case["id"], "passed": False, "quality_score": 0.0,
                "error": f"{e}\n{traceback.format_exc()}",
            })
        time.sleep(4)  # be polite to the free-tier rate limit

    brief_results = []
    for case in BRIEF_TEST_CASES:
        try:
            brief_results.append(run_brief_case(case))
        except Exception as e:  # noqa: BLE001
            brief_results.append({
                "id": case["id"], "passed": False, "quality_score": 0.0,
                "error": f"{e}\n{traceback.format_exc()}",
            })
        time.sleep(4)

    def summarize(results: list[dict]) -> dict:
        n = len(results)
        passed = sum(1 for r in results if r.get("passed"))
        avg_q = sum(r.get("quality_score", 0.0) for r in results) / n if n else 0.0
        return {"total": n, "passed": passed, "failed": n - passed,
                "pass_rate": round(passed / n, 3) if n else 0.0,
                "avg_quality_score": round(avg_q, 3)}

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task1_triage": {"summary": summarize(triage_results), "cases": triage_results},
        "task2_account_brief": {"summary": summarize(brief_results), "cases": brief_results},
    }


def render_markdown(report: dict) -> str:
    lines = [f"# Eval Report\n\nGenerated: {report['generated_at']}\n"]
    for task_key, title in [("task1_triage", "Task 1 — Ticket Triage"),
                             ("task2_account_brief", "Task 2 — Account Brief")]:
        s = report[task_key]["summary"]
        lines.append(f"## {title}\n")
        lines.append(f"- Total cases: {s['total']}")
        lines.append(f"- Passed: {s['passed']}  |  Failed: {s['failed']}")
        lines.append(f"- Pass rate: {s['pass_rate']}")
        lines.append(f"- Avg quality score: {s['avg_quality_score']}\n")
        lines.append("| Case | Adversarial | Passed | Quality | Notes |")
        lines.append("|------|------------|--------|---------|-------|")
        for c in report[task_key]["cases"]:
            note = c.get("error") or c.get("judge_rationale") or "; ".join(c.get("rule_failures", [])) or ""
            note = note.replace("\n", " ")[:100]
            lines.append(
                f"| {c['id']} | {c.get('adversarial')} | {c.get('passed')} | "
                f"{c.get('quality_score')} | {note} |"
            )
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent.parent
    report = run_all()

    (repo_root / "eval_report.json").write_text(json.dumps(report, indent=2))
    (repo_root / "eval_report.md").write_text(render_markdown(report))

    print(render_markdown(report))
    print(f"\nWrote {repo_root / 'eval_report.json'} and {repo_root / 'eval_report.md'}")
