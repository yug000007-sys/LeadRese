import io
    import re
    import time
    from urllib.parse import quote_plus, urlparse

    import pandas as pd
    import requests
    import streamlit as st
    from bs4 import BeautifulSoup
    from duckduckgo_search import DDGS

    try:
        import google.generativeai as genai
    except Exception:
        genai = None


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

    SIC_NAICS_RULES = [
        {
            "keywords": ["aerospace", "aircraft", "defense", "missile", "aviation", "space"],
            "sic": "3721 / 3761",
            "naics": "336411 / 336414",
            "lob": "Aerospace and defense manufacturing, engineering, and support services.",
        },
        {
            "keywords": ["automotive", "vehicle", "motor", "car", "truck", "parts"],
            "sic": "3711 / 3714",
            "naics": "336111 / 336390",
            "lob": "Automotive manufacturing, parts, systems, or related services.",
        },
        {
            "keywords": ["software", "saas", "technology", "cloud", "it services", "cybersecurity"],
            "sic": "7372 / 7373",
            "naics": "541511 / 541512",
            "lob": "Software, IT services, cloud, or technology solutions.",
        },
        {
            "keywords": ["consulting", "business consulting", "management consulting"],
            "sic": "8742 / 8748",
            "naics": "541611",
            "lob": "Business, management, or professional consulting services.",
        },
        {
            "keywords": ["logistics", "transport", "freight", "warehouse", "supply chain"],
            "sic": "4731 / 4225",
            "naics": "488510 / 493110",
            "lob": "Logistics, freight, warehousing, or supply-chain services.",
        },
        {
            "keywords": ["manufacturer", "manufacturing", "factory", "industrial", "machinery"],
            "sic": "3999 / 3599",
            "naics": "339999 / 333249",
            "lob": "Industrial manufacturing or machinery-related operations.",
        },
        {
            "keywords": ["hospital", "healthcare", "medical", "clinic", "pharma"],
            "sic": "8062 / 2834",
            "naics": "622110 / 325412",
            "lob": "Healthcare, medical, pharmaceutical, or related services.",
        },
        {
            "keywords": ["bank", "financial", "insurance", "investment", "credit"],
            "sic": "6021 / 6411",
            "naics": "522110 / 524210",
            "lob": "Banking, financial, insurance, or investment services.",
        },
    ]


    st.set_page_config(page_title="Company Auto-Enrichment Tool", layout="wide")
    st.title("Company Auto-Enrichment Tool")
    st.caption("Upload Excel/CSV → web research → structured enrichment → download Excel.")


    def clean_value(value):
        if pd.isna(value):
            return ""
        return str(value).strip()


    def normalize_columns(df):
        rename_map = {}
        for c in df.columns:
            c2 = str(c).strip()
            low = c2.lower().replace(" ", "").replace("_", "")
            if low in ["company", "companyname", "name"]:
                rename_map[c] = "Company"
            elif low in ["city", "town"]:
                rename_map[c] = "City"
            elif low in ["state", "province", "region"]:
                rename_map[c] = "State"
            elif low in ["zip", "zipcode", "postal", "postalcode", "postcode"]:
                rename_map[c] = "Zip"
            elif low in ["country", "nation"]:
                rename_map[c] = "Country"
        df = df.rename(columns=rename_map)
        for col in INPUT_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df


    def safe_get(url, timeout=8):
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        }
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            if r.status_code == 200 and r.text:
                return r.text[:50000]
        except Exception:
            return ""
        return ""


    def ddg_search(query, max_results=5):
        results = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "href": r.get("href", ""),
                        "body": r.get("body", ""),
                    })
        except Exception as e:
            st.warning(f"Search failed for query: {query}. Error: {e}")
        return results


    def make_queries(company, city, state, zip_code, country):
        parts = [company, city, state, zip_code, country]
        base = " ".join([p for p in parts if p]).strip()
        queries = [
            f'{base} official address phone website',
            f'{base} company profile address',
            f'{company} {country} official website address',
        ]
        if city or zip_code:
            queries.insert(0, f'"{company}" "{city}" "{zip_code}" "{country}" address phone')
        return [q.strip() for q in queries if q.strip()]


    def extract_text_from_url(url):
        html = safe_get(url)
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()
        text = " ".join(soup.get_text(" ").split())
        return text[:12000]


    def find_phone(text):
        patterns = [
            r"\+\d{1,3}[\s\-.]?\(?\d{1,4}\)?[\s\-.]?\d{2,5}[\s\-.]?\d{2,5}[\s\-.]?\d{2,6}",
            r"\(?\d{3}\)?[\s\-.]\d{3}[\s\-.]\d{4}",
            r"\d{2,5}[\s\-.]\d{2,5}[\s\-.]\d{3,5}",
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                return m.group(0).strip()
        return "Not publicly disclosed"


    def find_website(search_results):
        bad_domains = ["google.", "facebook.", "linkedin.", "x.com", "twitter.", "bloomberg.", "dnb.", "zoominfo.", "yelp.", "mapquest."]
        for r in search_results:
            href = r.get("href", "")
            if not href:
                continue
            domain = urlparse(href).netloc.lower()
            if domain and not any(bad in domain for bad in bad_domains):
                return f"{urlparse(href).scheme}://{domain}".rstrip("/")
        return "Not verified"


    def classify_business(text):
        low = text.lower()
        for rule in SIC_NAICS_RULES:
            if any(k in low for k in rule["keywords"]):
                return rule["sic"], rule["naics"], rule["lob"]
        return "Needs manual verification", "Needs manual verification", "General business operations; verify line of business from official source."


    def simple_address_guess(text, city, state, zip_code, country):
        # Conservative extraction. If no clear match, mark needs review.
        snippets = []
        tokens = [t for t in [city, state, zip_code, country] if t]
        for token in tokens:
            idx = text.lower().find(token.lower())
            if idx >= 0:
                start = max(0, idx - 120)
                end = min(len(text), idx + 180)
                snippets.append(text[start:end])
        if snippets:
            s = max(snippets, key=len)
            s = re.sub(r"\s+", " ", s).strip()
            # Remove obvious UI text.
            if len(s) > 40:
                return s[:280]
        return "Needs manual verification"


    def confidence_score(company, city, country, search_results, website, address):
        score = 0
        combined = " ".join([r.get("title", "") + " " + r.get("body", "") + " " + r.get("href", "") for r in search_results]).lower()
        if company and company.lower() in combined:
            score += 35
        if city and city.lower() in combined:
            score += 20
        if country and country.lower() in combined:
            score += 15
        if website and website not in ["Not verified", ""]:
            score += 15
        if address and "manual" not in address.lower() and "needs" not in address.lower():
            score += 15
        if score >= 75:
            return "High"
        if score >= 45:
            return "Medium"
        return "Low"


    def gemini_enrich(api_key, company, city, state, zip_code, country, search_results, page_text):
        if not api_key or genai is None:
            return None
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            evidence = {
                "input": {
                    "Company": company,
                    "City": city,
                    "State": state,
                    "Zip": zip_code,
                    "Country": country,
                },
                "search_results": search_results[:5],
                "page_text_excerpt": page_text[:8000],
            }
            prompt = f"""
You are a B2B company research assistant. Return only valid JSON.

Task: Enrich this company record using the evidence. Prefer official company website or trusted business directories.
Do not invent. If not found, use "Not publicly disclosed" or "Needs manual verification".

Required JSON keys:
Company, Address, City, State, Zip, Country, PhoneResearch, Website, SIC, NAICS,
NoOfEmployees(This site only), LineOfBusiness, ParentName, Confidence, SourceURL, Remarks

Evidence:
{json.dumps(evidence, ensure_ascii=False)}
"""
            response = model.generate_content(prompt)
            raw = response.text.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            data = json.loads(raw)
            return data
        except Exception as e:
            return {"_error": str(e)}


    def enrich_one(row, use_gemini, api_key):
        company = clean_value(row.get("Company", ""))
        city = clean_value(row.get("City", ""))
        state = clean_value(row.get("State", ""))
        zip_code = clean_value(row.get("Zip", ""))
        country = clean_value(row.get("Country", ""))

        queries = make_queries(company, city, state, zip_code, country)
        all_results = []
        for q in queries[:3]:
            all_results.extend(ddg_search(q, max_results=4))
            time.sleep(0.4)

        # Deduplicate results.
        seen = set()
        search_results = []
        for r in all_results:
            href = r.get("href", "")
            if href and href not in seen:
                seen.add(href)
                search_results.append(r)

        website = find_website(search_results)
        source_url = search_results[0]["href"] if search_results else f"https://duckduckgo.com/?q={quote_plus(queries[0])}"

        page_text = ""
        for r in search_results[:3]:
            page_text += "\n\nSOURCE: " + r.get("href", "") + "\n"
            page_text += extract_text_from_url(r.get("href", ""))[:6000]

        if use_gemini and api_key:
            ai_result = gemini_enrich(api_key, company, city, state, zip_code, country, search_results, page_text)
            if ai_result and "_error" not in ai_result:
                clean = {col: ai_result.get(col, "") for col in OUTPUT_COLUMNS}
                for col in OUTPUT_COLUMNS:
                    if not clean.get(col):
                        clean[col] = "Needs manual verification"
                return clean
            elif ai_result and "_error" in ai_result:
                st.warning(f"Gemini failed for {company}: {ai_result['_error']}")

        combined_text = " ".join([r.get("title", "") + " " + r.get("body", "") for r in search_results]) + " " + page_text
        phone = find_phone(combined_text)
        sic, naics, lob = classify_business(combined_text)
        address = simple_address_guess(combined_text, city, state, zip_code, country)
        confidence = confidence_score(company, city, country, search_results, website, address)

        parent = "Needs manual verification"
        if "subsidiary" in combined_text.lower() or "parent" in combined_text.lower():
            parent = "Possible parent/subsidiary relationship found; verify source."

        return {
            "Company": company,
            "Address": address,
            "City": city if city else "Needs manual verification",
            "State": state if state else "Needs manual verification",
            "Zip": zip_code if zip_code else "Needs manual verification",
            "Country": country if country else "Needs manual verification",
            "PhoneResearch": phone,
            "Website": website,
            "SIC": sic,
            "NAICS": naics,
            "NoOfEmployees(This site only)": "Not publicly disclosed",
            "LineOfBusiness": lob,
            "ParentName": parent,
            "Confidence": confidence,
            "SourceURL": source_url,
            "Remarks": "Auto-enriched from public web search. Review Low/Medium confidence records before use.",
        }


    def to_excel_bytes(df):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Enriched")
        return output.getvalue()


    with st.sidebar:
        st.header("Settings")
        max_rows_default = 25
        delay = st.number_input("Delay between records, seconds", min_value=0.0, max_value=10.0, value=1.0, step=0.5)
        use_gemini = st.checkbox("Use Gemini AI if API key is configured", value=True)
        st.caption("For Streamlit Cloud, add GEMINI_API_KEY in App settings → Secrets.")
        api_key = ""
        try:
            api_key = st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            api_key = ""
        if not api_key:
            api_key = st.text_input("Optional Gemini API Key", type="password")
        st.warning("Free web search/scraping can be slow or blocked. Process small batches first.")


    uploaded = st.file_uploader("Upload Excel or CSV", type=["xlsx", "csv"])

    if uploaded:
        try:
            if uploaded.name.lower().endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)
            df = normalize_columns(df)

            st.subheader("Input preview")
            st.dataframe(df[INPUT_COLUMNS].head(50), use_container_width=True)

            max_rows = st.number_input("Rows to process now", min_value=1, max_value=len(df), value=min(len(df), max_rows_default), step=1)

            if st.button("Start auto-enrichment"):
                work_df = df.head(max_rows).copy()
                results = []
                progress = st.progress(0)
                status = st.empty()

                for i, (_, row) in enumerate(work_df.iterrows(), start=1):
                    company = clean_value(row.get("Company", ""))
                    status.write(f"Processing {i}/{len(work_df)}: {company}")
                    results.append(enrich_one(row, use_gemini, api_key))
                    progress.progress(i / len(work_df))
                    time.sleep(delay)

                out_df = pd.DataFrame(results)
                out_df = out_df[OUTPUT_COLUMNS]

                st.success("Done.")
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
            st.error("App error")
            st.exception(e)
    else:
        sample = pd.DataFrame([
            {"Company": "Boeing", "City": "Tanner", "State": "AL", "Zip": "35671", "Country": "USA"},
            {"Company": "BOEL", "City": "Osaka-Shi", "State": "", "Zip": "", "Country": "Japan"},
        ])
        st.subheader("Sample input format")
        st.dataframe(sample, use_container_width=True)
        st.download_button("Download sample CSV", data=sample.to_csv(index=False).encode("utf-8"), file_name="sample_input.csv", mime="text/csv")

    st.divider()
    st.markdown("""
    ### Notes
    - Best input: `Company + City + State + Zip + Country`
    - Minimum input: `Company + Country`
    - Records with only company/country may return headquarters or ambiguous results.
    - Review all Low/Medium confidence rows.
    - For better accuracy, use Gemini API key in Streamlit Secrets.
    """)
