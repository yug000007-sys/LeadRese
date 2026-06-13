import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Company Enrichment Tool", layout="wide")

st.title("Company Enrichment Tool")
st.success("App is working successfully.")

st.write("Upload your company Excel/CSV file and download the formatted output.")

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

def clean(value):
    if pd.isna(value):
        return ""
    return str(value).strip()

def normalize_columns(df):
    rename_map = {}
    for col in df.columns:
        key = str(col).strip().lower().replace(" ", "").replace("_", "")
        if key in ["company", "companyname", "name"]:
            rename_map[col] = "Company"
        elif key in ["city", "town"]:
            rename_map[col] = "City"
        elif key in ["state", "province", "region"]:
            rename_map[col] = "State"
        elif key in ["zip", "zipcode", "postal", "postalcode", "postcode"]:
            rename_map[col] = "Zip"
        elif key in ["country", "nation"]:
            rename_map[col] = "Country"

    df = df.rename(columns=rename_map)

    for col in INPUT_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    return df

def create_output(df):
    rows = []

    for _, row in df.iterrows():
        company = clean(row.get("Company", ""))
        city = clean(row.get("City", ""))
        state = clean(row.get("State", ""))
        zip_code = clean(row.get("Zip", ""))
        country = clean(row.get("Country", ""))

        search_query = "+".join(
            [x for x in [company, city, state, zip_code, country, "official address phone website"] if x]
        )

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
            "SourceURL": f"https://www.google.com/search?q={search_query}",
            "Remarks": "Clean Streamlit Cloud version. Auto-research can be added after app runs correctly.",
        })

    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)

def excel_bytes(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Enriched")
    return output.getvalue()

uploaded_file = st.file_uploader("Upload Excel or CSV", type=["xlsx", "csv"])

if uploaded_file is None:
    sample = pd.DataFrame([
        {"Company": "Boeing", "City": "Tanner", "State": "AL", "Zip": "35671", "Country": "USA"},
        {"Company": "BOEL", "City": "Osaka-Shi", "State": "", "Zip": "", "Country": "Japan"},
    ])

    st.subheader("Sample Input")
    st.dataframe(sample, use_container_width=True)

    st.download_button(
        "Download Sample CSV",
        data=sample.to_csv(index=False).encode("utf-8"),
        file_name="sample_input.csv",
        mime="text/csv",
    )

else:
    try:
        if uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        df = normalize_columns(df)

        st.subheader("Input Preview")
        st.dataframe(df[INPUT_COLUMNS].head(100), use_container_width=True)

        rows_to_process = st.number_input(
            "Rows to process",
            min_value=1,
            max_value=len(df),
            value=min(len(df), 100),
            step=1,
        )

        if st.button("Generate Output"):
            output_df = create_output(df.head(rows_to_process))

            st.subheader("Output Preview")
            st.dataframe(output_df, use_container_width=True)

            st.download_button(
                "Download Excel",
                data=excel_bytes(output_df),
                file_name="company_enrichment_output.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

            st.download_button(
                "Download CSV",
                data=output_df.to_csv(index=False).encode("utf-8"),
                file_name="company_enrichment_output.csv",
                mime="text/csv",
            )

    except Exception as error:
        st.error("Error processing file")
        st.exception(error)
