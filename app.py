import io
    import json
    import re
    import time
    from urllib.parse import quote_plus, urlparse

    import pandas as pd
    import requests
    import streamlit as st
    from bs4 import BeautifulSoup


    st.set_page_config(page_title="Company Auto-Enrichment Tool", layout="wide")

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
        (["aerospace", "aircraft", "defense", "missile", "aviation", "space"], "3721 / 3761", "336411 / 336414", "Aerospace and defense manufacturing, engineering, and support services."),
        (["automotive", "vehicle", "motor", "car", "truck", "parts"], "3711 / 3714", "336111 / 336390", "Automotive manufacturing, parts, systems, or related services."),
        (["software", "saas", "technology", "cloud", "it services", "cybersecurity"], "7372 / 7373", "541511 / 541512", "Software, IT services, cloud, or technology solutions."),
        (["consulting", "business consulting", "management consulting"], "8742 / 8748", "541611", "Business, management, or professional consulting services."),
        (["logistics", "transport", "freight", "warehouse", "supply chain"], "4731 / 4225", "488510 / 493110", "Logistics, freight, warehousing, or supply-chain services."),
        (["manufacturer", "manufacturing", "factory", "industrial", "machinery"], "3999 / 3599", "339999 / 333249", "Industrial manufacturing or machinery-related operations."),
        (["hospital", "healthcare", "medical", "clinic", "pharma"], "8062 / 2834", "622110 / 325412", "Healthcare, medical, pharmaceutical, or related services."),
        (["bank", "financial", "insurance", "investment", "credit"], "6021 / 6411", "522110 / 524210", "Banking, financial, insurance, or investment services."),
    ]


    def clean_value(value):
        if pd.isna(value):
            return ""
        return str(value).strip()


    def normalize_columns(df):
        rename_map = {}
        for c in df.columns:
            low = str(c).strip().lower().replace(" ", "").replace("_", "")
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


    def search_duckduckgo_html(query, max_results=5):
        """No extra dependency. Uses DuckDuckGo HTML page and parses result links."""
        results = []
        url = "https://duckduckgo.com/html/?q=" + quote_plus(query)
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            r = requests.get(url, headers=headers, timeout=12)
            soup = BeautifulSoup(r.text, "html.parser")
            items = soup.select(".result")
            for item in items[:max_results]:
                link = item.select_one(".result__a")
                snippet = item.select_one(".result__snippet")
                if not link:
                    continue
                href = link.get("href", "")
                title = link.get_text(" ", strip=True)
                body = snippet.get_text(" ", strip=True) if snippet else ""
                if href:
                    results.append({"title": title, "href": href, "body": body})
        except Exception as e:
            results.append({"title": "Search error", "href": "", "body": str(e)})
        return results


    def safe_get_text(url):
        if not url or not url.startswith("http"):
            return ""
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                return ""
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            return " ".join(soup.get_text(" ").split())[:12000]
        except Exception:
            return ""


    def make_queries(company, city, state, zip_code, country):
        base = " ".join([x for x in [company, city, state, zip_code, country] if x]).strip()
        queries = [
            f"{base} official address phone website",
            f"{base} company profile address",
            f"{company} {country} official website headquarters address",
        ]
        if city or zip_code:
            queries.insert(0, f'"{company}" "{city}" "{zip_code}" "{country}" address phone')
        return [q for q in queries if q.strip()]


    def find_website(results):
        blocked = ["duckduckgo.", "google.", "facebook.", "linkedin.", "x.com", "twitter.", "bloomberg.", "dnb.", "zoominfo."]
        for r in results:
            href = r.get("href", "")
            if not href.startswith("http"):
                continue
            netloc = urlparse(href).netloc.lower()
            if netloc and not any(b in netloc for b in blocked):
                return f"{urlparse(href).scheme}://{netloc}"
        return "Not verified"


    def find_phone(text):
        patterns = [
            r"\+\d{1,3}[\s\-.]?\(?\d{1,5}\)?[\s\-.]?\d{2,5}[\s\-.]?\d{2,5}[\s\-.]?\d{2,6}",
            r"\(?\d{3}\)?[\s\-.]\d{3}[\s\-.]\d{4}",
        ]
        for pattern in patterns:
            m = re.search(pattern, text)
            if m:
                return m.group(0).strip()
        return "Not publicly disclosed"


    def classify_business(text):
        low = text.lower()
        for keywords, sic, naics, lob in SIC_NAICS_RULES:
            if any(k in low for k in keywords):
                return sic, naics, lob
        return "Needs manual verification", "Needs manual verification", "General business operations; verify line of business from official source."


    def guess_address(text, city, state, zip_code, country):
        tokens = [t for t in [city, state, zip_code, country] if t]
        best = ""
        low = text.lower()
        for token in tokens:
            idx = low.find(token.lower())
            if idx >= 0:
                snippet = text[max(0, idx - 120): min(len(text), idx + 180)]
                if len(snippet) > len(best):
                    best = snippet
        if best:
            return re.sub(r"\s+", " ", best).strip()[:280]
        return "Needs manual verification"


    def confidence(company, city, country, results, address, website):
        combined = " ".join([r.get("title", "") + " " + r.get("body", "") + " " + r.get("href", "") for r in results]).lower()
        score = 0
        if company and company.lower() in combined:
            score += 35
        if city and city.lower() in combined:
            score += 20
        if country and country.lower() in combined:
            score += 15
        if website != "Not verified":
            score += 15
        if "Needs manual" not in address:
            score += 15
        if score >= 75:
            return "High"
        if score >= 45:
            return "Medium"
        return "Low"


    def gemini_json(api_key, payload):
        if not api_key:
            return None
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = """
Return only valid JSON with these keys:
Company, Address, City, State, Zip, Country, PhoneResearch, Website, SIC, NAICS,
NoOfEmployees(This site only), LineOfBusiness, ParentName, Confidence, SourceURL, Remarks.

Do not invent. Use "Needs manual verification" or "Not publicly disclosed" when missing.

Evidence:
""" + json.dumps(payload, ensure_ascii=False)
            response = model.generate_content(prompt)
            raw = response.text.strip().replace("```json", "").replace("```", "").strip()
            return json.loads(raw)
        except Exception as e:
            st.warning(f"Gemini step skipped: {e}")
            return None


    def enrich(row, use_gemini, api_key):
        company = clean_value(row.get("Company", ""))
        city = clean_value(row.get("City", ""))
        state = clean_value(row.get("State", ""))
        zip_code = clean_value(row.get("Zip", ""))
        country = clean_value(row.get("Country", ""))

        queries = make_queries(company, city, state, zip_code, country)
        results = []
        for q in queries[:2]:
            results.extend(search_duckduckgo_html(q, max_results=4))
            time.sleep(0.5)

        seen = set()
        deduped = []
        for r in results:
            href = r.get("href", "")
            if href not in seen:
                seen.add(href)
                deduped.append(r)
        results = deduped[:8]

        website = find_website(results)
        source = results[0].get("href", "") if results else "https://duckduckgo.com/?q=" + quote_plus(queries[0])

        page_text = ""
        for r in results[:2]:
            page_text += "\n" + safe_get_text(r.get("href", ""))

        combined = " ".join([r.get("title", "") + " " + r.get("body", "") for r in results]) + " " + page_text

        base_result = {
            "Company": company,
            "Address": guess_address(combined, city, state, zip_code, country),
            "City": city or "Needs manual verification",
            "State": state or "Needs manual verification",
            "Zip": zip_code or "Needs manual verification",
            "Country": country or "Needs manual verification",
            "PhoneResearch": find_phone(combined),
            "Website": website,
            "SIC": "",
            "NAICS": "",
            "NoOfEmployees(This site only)": "Not publicly disclosed",
            "LineOfBusiness": "",
            "ParentName": "Needs manual verification",
            "Confidence": "",
            "SourceURL": source,
            "Remarks": "Auto-enriched from public search. Review before use.",
        }

        sic, naics, lob = classify_business(combined)
        base_result["SIC"] = sic
        base_result["NAICS"] = naics
        base_result["LineOfBusiness"] = lob
        base_result["Confidence"] = confidence(company, city, country, results, base_result["Address"], website)

        if use_gemini and api_key:
            payload = {"input": dict(row), "search_results": results, "page_text_excerpt": combined[:8000], "draft": base_result}
            ai = gemini_json(api_key, payload)
            if ai:
                for col in OUTPUT_COLUMNS:
                    base_result[col] = ai.get(col, base_result.get(col, "Needs manual verification"))

        return base_result


    def to_excel_bytes(df):
        bio = io.BytesIO()
        with pd.ExcelWriter(bio, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Enriched")
        return bio.getvalue()


    st.title("Company Auto-Enrichment Tool")
    st.caption("Safe Streamlit Cloud version. Upload Excel/CSV and download enriched output.")

    with st.sidebar:
        st.header("Settings")
        rows_default = st.number_input("Default rows to process", 1, 100, 10)
        delay = st.number_input("Delay per record", 0.0, 5.0, 1.0, 0.5)
        use_gemini = st.checkbox("Use Gemini if API key is available", value=False)
        api_key = ""
        try:
            api_key = st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            api_key = ""
        if not api_key:
            api_key = st.text_input("Optional Gemini API key", type="password")

    uploaded = st.file_uploader("Upload Excel or CSV", type=["xlsx", "csv"])

    if uploaded:
        try:
            if uploaded.name.lower().endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)
            df = normalize_columns(df)

            if "Company" not in df.columns:
                st.error("Missing Company column.")
                st.stop()

            st.subheader("Input preview")
            st.dataframe(df[INPUT_COLUMNS].head(50), use_container_width=True)

            max_rows = st.number_input("Rows to process now", 1, len(df), min(len(df), int(rows_default)))

            if st.button("Start enrichment"):
                results = []
                progress = st.progress(0)
                status = st.empty()
                work = df.head(max_rows)

                for i, (_, row) in enumerate(work.iterrows(), start=1):
                    status.write(f"Processing {i}/{len(work)}: {clean_value(row.get('Company',''))}")
                    results.append(enrich(row, use_gemini, api_key))
                    progress.progress(i / len(work))
                    time.sleep(delay)

                out = pd.DataFrame(results)[OUTPUT_COLUMNS]
                st.success("Done")
                st.dataframe(out, use_container_width=True)

                st.download_button(
                    "Download Excel",
                    data=to_excel_bytes(out),
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
            st.error("The app error is shown below. Copy this if you need help.")
            st.exception(e)
    else:
        sample = pd.DataFrame([
            {"Company": "Boeing", "City": "Tanner", "State": "AL", "Zip": "35671", "Country": "USA"},
            {"Company": "BOEL", "City": "Osaka-Shi", "State": "", "Zip": "", "Country": "Japan"},
        ])
        st.subheader("Sample input")
        st.dataframe(sample, use_container_width=True)
        st.download_button("Download sample CSV", sample.to_csv(index=False).encode("utf-8"), "sample_input.csv", "text/csv")

    st.info("For Streamlit Cloud, process small batches first: 5–25 rows. Free search may be blocked or slow.")
