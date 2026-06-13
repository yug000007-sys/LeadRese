import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Company Enrichment Tool", layout="wide")

st.title("Company Enrichment Tool")
st.success("App loaded successfully.")
st.caption("Upload Excel/CSV, preview records, generate output template, and download Excel.")

INPUT_COLUMNS = ["Company", "City", "State", "Zip", "Country"]

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

def clean(v):
    if pd.isna(v):
        return ""
    return str(v).strip()

def normalize_columns(df):
    rename = {}
    for col in df.columns:
        key = str(col).strip().lower().replace(" ", "").replace("_", "")
        if key in ["company", "companyname", "name"]:
            rename[col] = "Company"
        elif key in ["city", "town"]:
            rename[col] = "City"
        elif key in ["state", "province", "region"]:
            rename[col] = "State"
        elif key in ["zip", "zipcode", "postal", "postalcode", "postcode"]:
            rename[col] = "Zip"
        elif key in ["country", "nation"]:
            rename[col] = "Country"
    df = df.rename(columns=rename)
    for col in INPUT_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df

def make_output(df):
    rows = []
    for _, r in df.iterrows():
        company = clean(r.get("Company", ""))
        city = clean(r.get("City", ""))
        state = clean(r.get("State", ""))
        zip_code = clean(r.get("Zip", ""))
        country = clean(r.get("Country", ""))

        query = "+".join([x for x in [company, city, state, zip_code, country, "official address phone website"] if x])
        source = f"https://www.google.com/search?q={query}"

        rows.append({
            "Company": company,
            "Address": "Needs research",
            "City": city or "Needs research",
            "State": state or "Needs research",
            "Zip": zip_code or "Needs research",
            "Country": country or "Needs research",
            "PhoneResearch": "Needs research",
            "Website": "Needs research",
            "SIC": "Needs classification",
            "NAICS": "Needs classification",
            "NoOfEmployees(This site only)": "Not publicly disclosed",
            "LineOfBusiness": "Needs research",
            "ParentName": "Needs research",
            "Confidence": "Low",
            "SourceURL": source,
            "Remarks": "Stable version. Use SourceURL for manual/AI research. Auto-research can be added after deployment works.",
        })
    return pd.DataFrame(rows)[OUTPUT_COLUMNS]

def to_excel(df):
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Enriched")
    return bio.getvalue()

with st.sidebar:
    st.header("Status")
    st.write("Version: ultra-stable")
    st.write("Dependencies: streamlit, pandas, openpyxl only")

uploaded = st.file_uploader("Upload Excel or CSV", type=["xlsx", "csv"])

if uploaded:
    try:
        if uploaded.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded)
        else:
            df = pd.read_excel(uploaded)

        df = normalize_columns(df)

        st.subheader("Input preview")
        st.dataframe(df[INPUT_COLUMNS].head(100), use_container_width=True)

        max_rows = st.number_input("Rows to process", 1, len(df), min(len(df), 100))

        if st.button("Generate output file"):
            out = make_output(df.head(max_rows))
            st.subheader("Output preview")
            st.dataframe(out, use_container_width=True)

            st.download_button(
                "Download Excel",
                data=to_excel(out),
                file_name="company_enrichment_output.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            st.download_button(
                "Download CSV",
                data=out.to_csv(index=False).encode("utf-8"),
                file_name="company_enrichment_output.csv",
                mime="text/csv",
            )

    except Exception as e:
        st.error("File processing error")
        st.exception(e)
else:
    sample = pd.DataFrame([
        {"Company": "Boeing", "City": "Tanner", "State": "AL", "Zip": "35671", "Country": "USA"},
        {"Company": "BOEL", "City": "Osaka-Shi", "State": "", "Zip": "", "Country": "Japan"},
    ])
    st.subheader("Sample input")
    st.dataframe(sample, use_container_width=True)
    st.download_button(
        "Download sample CSV",
        data=sample.to_csv(index=False).encode("utf-8"),
        file_name="sample_input.csv",
        mime="text/csv",
    )

st.info("First confirm this app opens on Streamlit Cloud. Then we can add auto-research safely.")
