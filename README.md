# Support & TAM AI Toolkit

AI-powered tooling for Technical Support and TAM teams: an intelligent
ticket triage agent, a TAM account health summariser, and an evaluation
harness to keep both honest — built on Google Gemini's free tier with
zero paid infrastructure.

## What's here

| Component | Location |
|-----------|----------|
| Ticket triage agent | `src/triage/agent.py` + `POST /triage` in `src/api.py` |
| TAM account brief | `src/account_brief/summarizer.py` + `GET /account-brief/{id}` |
| Eval harness | `src/eval/harness.py` → `eval_report.md` / `eval_report.json` |
| Design note | [`DESIGN_NOTE.md`](./DESIGN_NOTE.md) |
| Streamlit UI | `app_streamlit.py` |
| CI eval on push | `.github/workflows/eval.yml` |
| Prompt versioning | `prompts/*.py` (each has a `VERSION` + changelog docstring) |

## Setup

Requires Python 3.11+.

```bash
git clone <this-repo-url>
cd support-tam-ai-toolkit
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and add a free Gemini API key from https://aistudio.google.com/apikey
```

All model calls use Google Gemini's free tier (`gemini-3.5-flash-lite`).
No other paid service is required. Retrieval (the KB lookup) runs
entirely locally via TF-IDF — no embedding API, no extra cost, no model
download.

## Sample run — ticket triage

As a Python function:
```bash
python src/triage/agent.py
```
Runs a demo ticket about a DataBridge Pro connection timeout and prints
the structured triage JSON (category, urgency, KB match, draft response).

As a REST API:
```bash
uvicorn src.api:app --reload
# then, in another terminal:
curl -X POST http://localhost:8000/triage \
  -H "Content-Type: application/json" \
  -d '{"subject": "Unable to connect DataBridge Pro to Connectors", \
       "body": "ERR_CONNECTION_TIMEOUT after 30s, impacting 47 users in Production.", \
       "plan_tier": "Enterprise"}'
```
Interactive API docs at `http://localhost:8000/docs`.

## Sample run — account brief

```bash
python src/account_brief/summarizer.py
```
Generates a brief for `ACC-7397` (one of the few accounts in this dataset
with an actual linked ticket — see note below) and prints the structured
JSON (executive summary, quote-justified risk flags, talking points).

Or via the API: `GET http://localhost:8000/account-brief/ACC-7397`

## Sample run — eval harness

```bash
python src/eval/harness.py
```
Runs 6 triage test cases + 5 account-brief test cases (each set includes
an adversarial case), scores them with rule-based checks + LLM-as-judge,
and writes `eval_report.json` and `eval_report.md` to the repo root.

## Streamlit UI

```bash
streamlit run app_streamlit.py
```
A thin UI a non-technical TAM or support agent could actually use —
paste a ticket in, or pick an account, and get a formatted result
instead of raw JSON.

## A data-quality note worth knowing before you demo this

Ticket `account_id`s don't always match an account record in this
dataset — in practice, **only 4 of the 50 accounts** have any ticket at
all linked to them in this snapshot (`ACC-7397`, `ACC-1785`, `ACC-3336`,
`ACC-5748`), each with exactly one ticket. This is handled gracefully
throughout (`get_account_tickets` returns `[]`, the brief notes the data
gap explicitly rather than fabricating history), but it's worth knowing
going in so a demo account is picked deliberately rather than at random.

## Project structure
