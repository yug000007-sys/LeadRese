# Company Enrichment Tool - DigitalOcean Ready

This is a Streamlit app for company enrichment workflow.

## What it does

- Upload Excel or CSV
- Reads columns: `Company`, `City`, `State`, `Zip`, `Country`
- Generates required output columns:
  - Company
  - Address
  - City
  - State
  - Zip
  - Country
  - PhoneResearch
  - Website
  - SIC
  - NAICS
  - NoOfEmployees(This site only)
  - LineOfBusiness
  - ParentName
  - Confidence
  - SourceURL
  - Remarks
- Downloads final Excel or CSV

## Important

This version is no-API and safe for deployment. It does not automatically scrape Google or use ChatGPT API.
It prepares research-ready records with search links and confidence fields.

## Run locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## DigitalOcean deployment

Use the commands in `deploy/install.sh`.

Main app file:

```text
app.py
```

Default app port:

```text
8501
```
