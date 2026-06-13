# Company Auto-Enrichment Tool for Streamlit Cloud

Upload an Excel/CSV file with company records, auto-enrich from public web search, and download the completed Excel file.

## Input columns

Required:

```text
Company
```

Recommended:

```text
Company, City, State, Zip, Country
```

The app will also understand similar names like `Company Name`, `PostalCode`, `Province`, etc.

## Output columns

```text
Company
Address
City
State
Zip
Country
PhoneResearch
Website
SIC
NAICS
NoOfEmployees(This site only)
LineOfBusiness
ParentName
Confidence
SourceURL
Remarks
```

## Deploy on Streamlit Community Cloud

1. Create a GitHub repository.
2. Upload all files from this ZIP to the repo root.
3. Go to Streamlit Community Cloud.
4. Click **New app**.
5. Select your repo.
6. Set **Main file path** to:

```text
app.py
```

7. Click **Deploy**.

## Optional Gemini API key

The app works with free DuckDuckGo-based search and rule extraction.

For much better structured results, add a Gemini API key:

1. Open your deployed Streamlit app.
2. Go to **Manage app**.
3. Open **Settings**.
4. Open **Secrets**.
5. Add:

```toml
GEMINI_API_KEY = "your_key_here"
```

6. Save and reboot the app.

You can get a Gemini key from Google AI Studio. Usage may be subject to Google's free-tier limits.

## Important limitations

- Free Streamlit Cloud can timeout on large batches.
- Free web search can be blocked or rate-limited.
- Process small batches first, such as 10 to 25 records.
- Always review Low/Medium confidence records.
- Company-only + country-only records may return HQ or ambiguous branch information.

## Run locally

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

On Windows:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
