# Company Auto-Enrichment Tool - Streamlit Cloud Safe Version

## Deploy

1. Upload all files to GitHub repo root.
2. Open Streamlit Community Cloud.
3. Select repo.
4. Main file path: `app.py`
5. Deploy.

## Input columns

Recommended:

```text
Company, City, State, Zip, Country
```

Minimum:

```text
Company, Country
```

## Optional Gemini

In Streamlit Cloud > Manage app > Secrets, add:

```toml
GEMINI_API_KEY = "your_key_here"
```

## Notes

Free Streamlit Cloud and free web search can be slow or blocked. Start with 5-25 rows.
