# Eval Report

Generated: 2026-08-27T06:52:19.244423+00:00

## Task 1 — Ticket Triage

- Total cases: 6
- Passed: 5  |  Failed: 1
- Pass rate: 0.833
- Avg quality score: 0.833

| Case | Adversarial | Passed | Quality | Notes |
|------|------------|--------|---------|-------|
| TC-01 | False | True | 1.0 | judge call failed: LLM output didn't match the expected schema: 1 validation error for JudgeVerdict  |
| TC-02 | False | False | 0.0 | judge call failed: LLM output didn't match the expected schema: 1 validation error for JudgeVerdict  |
| TC-03 | False | True | 1.0 | judge call failed: LLM output didn't match the expected schema: 1 validation error for JudgeVerdict  |
| TC-04 | False | True | 1.0 | judge call failed: LLM output didn't match the expected schema: 1 validation error for JudgeVerdict  |
| TC-05-adversarial | True | True | 1.0 | judge call failed: LLM output didn't match the expected schema: 1 validation error for JudgeVerdict  |
| TC-06-adversarial | True | True | 1.0 | judge call failed: LLM output didn't match the expected schema: 1 validation error for JudgeVerdict  |

## Task 2 — Account Brief

- Total cases: 5
- Passed: 2  |  Failed: 3
- Pass rate: 0.4
- Avg quality score: 0.4

| Case | Adversarial | Passed | Quality | Notes |
|------|------------|--------|---------|-------|
| BC-01 | False | False | 0.0 | LLM output didn't match the expected schema: 3 validation errors for RiskFlag signal   Field require |
| BC-02 | False | False | 0.0 | LLM output didn't match the expected schema: 3 validation errors for RiskFlag signal   Field require |
| BC-03 | False | True | 1.0 | judge call failed: LLM output didn't match the expected schema: 1 validation error for JudgeVerdict  |
| BC-04 | False | False | 0.0 | LLM output didn't match the expected schema: 3 validation errors for RiskFlag signal   Field require |
| BC-05-adversarial | True | True | 1.0 |  |
