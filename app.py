import io
import re
import time
from urllib.parse import quote_plus

import pandas as pd
import streamlit as st

OUTPUT_COLUMNS = [
    "Company",
    "Address",
    "City",
    "State",
    "Zip",
    "Country",
    "PhoneResearch",
    "Website",
    "SIC",
    "NAICS",
    "NoOfEmployees(This site only)",
    "LineOfBusiness",
    "ParentName",
    "Confidence",
    "SourceURL",
    "Remarks",
]

INPUT_COLUMNS = ["Company", "City", "State", "Zip", "Country"]

def clean_value(value):
    if pd.isna(value):
        return ""
    return str(value).strip()

def build_search_url(company, city="", state="", zip_code="", country=""):
    query = " ".join([company, city, state, zip_code, country, "official address phone website"]).strip()
    return "https://www.google.com/search?q=" + quote_plus(query)

def guess_website(company, country):
    slug = re.sub(r"[^a-z0-9]", "", company.lower())
    if not slug:
        return ""
    country = country.lower()
    if "japan" in country:
        return f"https://www.{slug}.co.jp"
    if "australia" in country:
        return f"https://www.{slug}.com.au"
    return f"https://www.{slug}.com"

def enrich_record(row):
    company = clean_value(row.get("Company", ""))
    city = clean_value(row.get("City", ""))
    state = clean_value(row.get("State", ""))
    zip_code = clean_value(row.get("Zip", ""))
    country = clean_value(row.get("Country", ""))

    search_url = build_search_url(company, city, state, zip_code, country)

    result = {
        "Company": company,
        "Address": "Needs research",
        "City": city if city else "Needs research",
        "State": state if state else "Needs research",
        "Zip": zip_code if zip_code else "Needs research",
        "Country": country if country else "Needs research",
        "PhoneResearch": "Needs research",
        "Website": guess_website(company, country),
        "SIC": "Needs classification",
        "NAICS": "Needs classification",
        "NoOfEmployees(This site only)": "Not publicly disclosed",
        "LineOfBusiness": "Needs research",
        "ParentName": "Needs research",
        "Confidence": "Low",
        "SourceURL": search_url,
        "Remarks": "Open SourceURL and verify. This no-API version prepares enrichment fields and research links.",
    }

    if company and city and country:
        result["Confidence"] = "Medium"
        result["Remarks"] = "Input has company/city/country. Verify official source before final use."
    elif company and country:
        result["Confidence"] = "Low"
        result["Remarks"] = "Only company/country available. Likely HQ search needed; location may be ambiguous."

    return result

def to_excel_bytes(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Enriched")
    return output.getvalue()

st.set_page_config(page_title="Company Enrichment Tool", layout="wide")
st.title("Company Enrichment Tool")
st.caption("DigitalOcean-ready Streamlit app: upload company list, generate research-ready enrichment output, download Excel.")

with st.expander("Required input columns", expanded=False):
    st.write(", ".join(INPUT_COLUMNS))
    st.write("Minimum recommended fields: Company + Country. Better: Company + City + State + Zip + Country.")

uploaded = st.file_uploader("Upload Excel or CSV", type=["xlsx", "csv"])

if uploaded:
    try:
        if uploaded.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded)
        else:
            df = pd.read_excel(uploaded)

        df.columns = [str(c).strip() for c in df.columns]

        if "Company" not in df.columns:
            st.error("Missing required column: Company")
            st.stop()

        for col in INPUT_COLUMNS:
            if col not in df.columns:
                df[col] = ""

        st.subheader("Preview input")
        st.dataframe(df.head(20), use_container_width=True)

        max_rows = st.number_input("Rows to process", min_value=1, max_value=len(df), value=min(len(df), 100), step=1)

        if st.button("Generate enrichment workbook"):
            rows = []
            progress = st.progress(0)

            work_df = df.head(max_rows).copy()
            total = len(work_df)

            for idx, (_, row) in enumerate(work_df.iterrows(), start=1):
                rows.append(enrich_record(row))
                progress.progress(idx / total)
                time.sleep(0.01)

            out_df = pd.DataFrame(rows)
            out_df = out_df[OUTPUT_COLUMNS]

            st.subheader("Output preview")
            st.dataframe(out_df, use_container_width=True)

            st.download_button(
                "Download Excel",
                data=to_excel_bytes(out_df),
                file_name="company_enrichment_output.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

            st.download_button(
                "Download CSV",
                data=out_df.to_csv(index=False).encode("utf-8"),
                file_name="company_enrichment_output.csv",
                mime="text/csv",
            )

    except Exception as e:
        st.error("The app crashed while reading or processing the file.")
        st.exception(e)
else:
    sample = pd.DataFrame([
        {"Company": "Boeing", "City": "Tanner", "State": "AL", "Zip": "35671", "Country": "USA"},
        {"Company": "BOEL", "City": "Osaka-Shi", "State": "", "Zip": "", "Country": "Japan"},
    ])
    st.subheader("Sample input format")
    st.dataframe(sample, use_container_width=True)
    st.download_button(
        "Download sample input CSV",
        data=sample.to_csv(index=False).encode("utf-8"),
        file_name="sample_input.csv",
        mime="text/csv",
    )

st.divider()
st.info(
    "This no-API version does not automatically scrape Google or ChatGPT. "
    "It creates structured enrichment rows, research links, confidence, and Excel export. "
    "A future version can add browser automation or AI API enrichment."
)
