import streamlit as st
import pandas as pd
import io
from lead_enricher.utils import read_csv_bytes
from lead_enricher.enrichment import enrich_contacts

st.set_page_config(page_title="lead-enricher-app", layout="wide")

st.title("Lead Enricher App")

with st.sidebar:
    st.header("Settings")
    num_papers = st.number_input("Number of papers/works to fetch", min_value=1, max_value=20, value=5)
    match_score_threshold = st.slider("Match score threshold", min_value=30, max_value=95, value=65)
    max_rows = st.number_input("Max rows to process", min_value=1, max_value=500, value=50)
    per_row_delay = st.number_input("Per-row delay (s) to avoid rate limits", min_value=0.0, max_value=5.0, value=0.5, step=0.1)
    safe_mode = st.checkbox("Safe mode (no LinkedIn scraping)", value=True, help="Do not attempt any LinkedIn scraping; LinkedIn URLs are stored only.")
    generate_hooks = st.checkbox("Generate email-ready hooks", value=True)

st.markdown("Upload an Apollo contacts CSV, run enrichment, preview and download the enriched CSV.")

uploaded = st.file_uploader("Upload CSV", type=["csv"])

if uploaded is not None:
    try:
        df = read_csv_bytes(uploaded)
    except Exception as e:
        st.error(f"Failed to read CSV: {e}")
        st.stop()

    st.success(f"Loaded {len(df)} rows")
    st.dataframe(df.head(5))

    settings = {
        "num_papers": int(num_papers),
        "match_score_threshold": int(match_score_threshold),
        "max_rows": int(max_rows),
        "per_row_delay": float(per_row_delay),
        "safe_mode": bool(safe_mode),
    }

    if st.button("Run enrichment"):
        progress = st.progress(0)
        status_text = st.empty()
        max_items = min(len(df), settings["max_rows"])
        enriched_rows = []
        for i in range(max_items):
            row = df.iloc[i:i+1]
            # call enrich_contacts on a single-row DataFrame
            out_df = enrich_contacts(row, settings)
            enriched_rows.append(out_df.iloc[0].to_dict())
            progress.progress(int(((i + 1) / max_items) * 100))
            status_text.text(f"Processed {i+1}/{max_items}")

        result_df = pd.DataFrame(enriched_rows)

        # Build privacy-safe output with email hooks when requested
        # Required output columns (plus minimal contact info retained):
        # First Name, Last Name, Title, Company, Email, LinkedIn, Website, Hook_Person, Hook_Company, Hook_Final
        original = df.reset_index(drop=True).iloc[:len(result_df)].copy()

        def get_orig(col_names, n):
            for cn in col_names:
                if cn in original.columns:
                    return original[cn].values
            return [None] * n

        n = len(result_df)
        out = pd.DataFrame()
        out["First Name"] = get_orig(["First Name", "first_name", "firstName"], n)
        out["Last Name"] = get_orig(["Last Name", "last_name", "lastName"], n)
        out["Title"] = get_orig(["Title", "title"], n)
        out["Company"] = get_orig(["Company Name", "company", "company_name"], n)
        out["Email"] = get_orig(["Email", "email"], n)
        # LinkedIn: prefer person linkedin url
        out["LinkedIn"] = get_orig(["Person Linkedin Url", "person_linkedin", "linkedin", "Person Linkedin"], n)
        out["Website"] = get_orig(["Website", "website"], n)

        # Hooks from enrichment output
        if generate_hooks:
            out["Hook_Person"] = result_df.get("Hook_Person", [""] * n).values
            out["Hook_Company"] = result_df.get("Hook_Company", [""] * n).values
            out["Hook_Final"] = result_df.get("Hook_Final", [""] * n).values
        else:
            out["Hook_Person"] = [""] * n
            out["Hook_Company"] = [""] * n
            out["Hook_Final"] = [""] * n

        combined = out

        st.subheader("Preview enriched results")
        st.dataframe(combined.head(10))

        if st.checkbox("Show debug info", value=False):
            debug_cols = ["Debug Name Used", "Debug Author Matched", "Debug Match Score", "Debug Papers Found", "Confidence Score"]
            dbg = result_df[[c for c in debug_cols if c in result_df.columns]]
            st.subheader("Debug info (per-row)")
            st.dataframe(dbg.head(10))

        if generate_hooks:
            st.subheader("Hook preview (first 10 rows)")
            st.table(combined["Hook_Final"].head(10))

        csv_bytes = combined.to_csv(index=False).encode("utf-8")
        st.download_button("Download enriched CSV", data=csv_bytes, file_name="enriched_contacts.csv", mime="text/csv")
