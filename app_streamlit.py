"""Bonus: thin Streamlit UI over Task 1 (triage) and Task 2 (account brief).

Run: streamlit run app_streamlit.py
"""

import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent / "src" / "triage"))
sys.path.insert(0, str(Path(__file__).resolve().parent / "src" / "account_brief"))

from data_loader import load_accounts  # noqa: E402
from triage.agent import triage_ticket  # noqa: E402
from account_brief.summarizer import AccountNotFoundError, generate_account_brief  # noqa: E402

st.set_page_config(page_title="Support & TAM AI Tools", layout="wide")
st.title("Support & TAM AI Tools")

tab1, tab2 = st.tabs(["🎫 Ticket Triage", "📊 Account Health Brief"])

with tab1:
    st.subheader("Triage a support ticket")
    subject = st.text_input("Subject", placeholder="e.g. Unable to connect DataBridge Pro to Connectors")
    body = st.text_area(
        "Body",
        height=150,
        placeholder="Paste the full ticket text here...",
    )
    plan_tier = st.selectbox("Plan tier (optional)", ["", "Starter", "Professional", "Business", "Enterprise"])

    if st.button("Triage ticket", type="primary"):
        if not subject and not body:
            st.warning("Enter a subject and/or body first.")
        else:
            with st.spinner("Classifying..."):
                try:
                    result = triage_ticket({
                        "subject": subject,
                        "body": body,
                        "plan_tier": plan_tier or None,
                    })
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Product Area", result["product_area"])
                    c2.metric("Category", result["category"])
                    c3.metric("Urgency", result["urgency"])

                    st.markdown(f"**Why this urgency:** {result['urgency_reasoning']}")
                    st.markdown(f"**Recommended team:** {result['recommended_responder_team']}")

                    if result["kb_match"]["matched"]:
                        st.success(
                            f"KB match: `{result['kb_match']['doc_path']}` — "
                            f"{result['kb_match']['heading_trail']}"
                        )
                    else:
                        st.info("No confident knowledge-base match found.")

                    st.markdown("**Draft first response:**")
                    st.text_area("draft", result["draft_first_response"], height=100, label_visibility="collapsed")

                    with st.expander("Raw JSON output"):
                        st.json(result)
                except Exception as e:  # noqa: BLE001
                    st.error(f"Triage failed: {e}")

with tab2:
    st.subheader("Generate a TAM account health brief")
    accounts = load_accounts()
    options = {f"{a['company']} ({a['account_id']})": a["account_id"] for a in accounts}
    choice = st.selectbox("Account", list(options.keys()))

    if st.button("Generate brief", type="primary"):
        account_id = options[choice]
        with st.spinner("Pulling account context and generating brief..."):
            try:
                brief = generate_account_brief(account_id)

                st.markdown(f"### {brief['company']} — Account Brief")
                if brief.get("data_completeness_note"):
                    st.warning(brief["data_completeness_note"])

                st.markdown("**Executive summary**")
                st.write(brief["executive_summary"])

                st.markdown("**Risks & flagged issues**")
                if brief["risks_and_flags"]:
                    for flag in brief["risks_and_flags"]:
                        sev_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(flag["severity"], "⚪")
                        st.markdown(
                            f"{sev_color} **{flag['signal']}** (ticket: {flag.get('ticket_id') or 'n/a'})  \n"
                            f"> {flag['justification_quote']}"
                        )
                else:
                    st.write("No risk flags identified.")

                st.markdown("**Recommended talking points**")
                for tp in brief["recommended_talking_points"]:
                    st.markdown(f"- {tp}")

                with st.expander("Raw JSON output"):
                    st.json(brief)
            except AccountNotFoundError as e:
                st.error(str(e))
            except Exception as e:  # noqa: BLE001
                st.error(f"Brief generation failed: {e}")
