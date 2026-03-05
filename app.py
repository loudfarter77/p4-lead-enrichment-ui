# app.py
import streamlit as st
import os
import pandas as pd
from pipeline import run_pipeline

st.set_page_config(
    page_title="Outreach Engine",
    page_icon="⚡",
    layout="centered"
)

st.title("⚡ Outreach Engine")
st.caption("Drop in your leads. Get personalised cold emails written directly back to your sheet.")

st.divider()

st.subheader("Configuration")

col1, col2 = st.columns(2)

with col1:
    sheet_id = st.text_input(
        "Google Sheet ID",
        placeholder="18Cj1ePp7BQMNfuSKiuT_U6VukY6SfL...",
        help="The long ID string from your Google Sheet URL"
    )

with col2:
    creds_path = st.text_input(
        "Service Account JSON path",
        value="service_account.json",
        help="Leave as default if the file is in your project folder"
    )

st.divider()

run_button = st.button("⚡ Generate Emails", type="primary")

if run_button:

    if not sheet_id:
        st.error("Please enter your Google Sheet ID.")
        st.stop()

    try:
    has_secrets = "gcp_service_account" in st.secrets
except Exception:
    has_secrets = False

if not has_secrets and not os.path.exists(creds_path):
    st.error("No credentials found. Add gcp_service_account to Streamlit Secrets or provide a local service_account.json.")
    st.stop()

if not has_secrets and not os.path.exists(creds_path):
    st.error("No credentials found. Add gcp_service_account to Streamlit Secrets or provide a local service_account.json.")
    st.stop()

    if not os.getenv("ANTHROPIC_API_KEY"):
        st.error("ANTHROPIC_API_KEY not found. Check your .env file.")
        st.stop()

    st.divider()
    st.subheader("Progress")
    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(current, total, company_name):
        pct = int(((current + 1) / total) * 100)
        progress_bar.progress(pct)
        status_text.text(f"Processing {current + 1} of {total}: {company_name}...")

    try:
        with st.spinner("Connecting to your sheet..."):
            results = run_pipeline(
                sheet_id=sheet_id,
                creds_path=creds_path,
                progress_callback=update_progress
            )

        progress_bar.progress(100)
        status_text.text("✅ All done!")

    except Exception as e:
        st.error(f"Something went wrong: {e}")
        st.exception(e)
        st.stop()

    st.divider()
    st.success(f"⚡ {len(results)} emails generated and written back to your sheet.")
    st.subheader(f"Results — {len(results)} leads processed")

    for result in results:
        with st.expander(f"📧 {result['Company']} — {result['Industry']}"):
            st.write(result['Generated Email'])

    st.divider()

    df_results = pd.DataFrame(results)
    csv = df_results.to_csv(index=False)

    st.download_button(
        label="⬇️ Download Results as CSV",
        data=csv,
        file_name="enriched_leads.csv",
        mime="text/csv"
    )
