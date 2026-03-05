# pipeline.py
import anthropic
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import time
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent / '.env')

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


def get_sheet_data(sheet_id: str, creds_path: str):
    creds = None

    # Try Streamlit Secrets first (production)
    try:
        import streamlit as st
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    except Exception:
        pass

    # Fall back to local file (development)
    if creds is None:
        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)

    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(sheet_id)
    worksheet = spreadsheet.sheet1
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    return df, worksheet


def enrich_lead(row: dict, anthropic_client) -> str:
    message = anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        system="""You are an expert cold email copywriter. 
Write short, personalised cold outreach emails for an AI automation agency.
The email should:
- Be 4-6 sentences maximum
- Reference the specific company and industry
- Mention one specific way AI automation could help their business. Specifically, my agency specialises in customer outreach and reactivation. It does not specialise in anything else.
- End with a simple call to action (a 15 minute call)
- Sound human, not salesy
- Change the tone depending on the industry. For example: use plain, practical language for trades (plumbing, construction). Use professional and data-driven language for logistics and finance. Use warm and community-focused language for food and hospitality.
Respond with just the email body, no subject line, no sign off.""",
        messages=[
            {
                "role": "user",
                "content": f"Write a cold email for this company:\nCompany: {row.get('company_name', '')}\nIndustry: {row.get('industry', '')}\nDescription: {row.get('description', '')}"
            }
        ]
    )
    return message.content[0].text


def write_email_to_sheet(worksheet, row_index: int, email: str):
    cell = f'D{row_index + 2}'
    worksheet.update([[email]], cell)


def run_pipeline(sheet_id: str, creds_path: str, progress_callback=None) -> list:
    # Get API key — try Streamlit Secrets first, then local .env
    api_key = None
    try:
        import streamlit as st
        api_key = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        pass

    if not api_key:
        api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found.")

    anthropic_client = anthropic.Anthropic(api_key=api_key)
    df, worksheet = get_sheet_data(sheet_id, creds_path)

    if df.empty:
        raise ValueError("Sheet is empty or has no data rows.")

    results = []

    for i, row in df.iterrows():
        company_name = row.get('company_name', f'Row {i+2}')

        if progress_callback:
            progress_callback(i, len(df), company_name)

        email = enrich_lead(row.to_dict(), anthropic_client)
        write_email_to_sheet(worksheet, i, email)

        results.append({
            'Company': company_name,
            'Industry': row.get('industry', ''),
            'Description': row.get('description', ''),
            'Generated Email': email
        })

        time.sleep(1)

    return results
