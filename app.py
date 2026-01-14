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

        # Keep only selected Apollo columns from the original export
        keep_cols = [
            "First Name",
            "Last Name",
            "Title",
            "Company Name",
            "Email",
            "Seniority",
            "Corporate Phone",
            "Industry",
            "Person Linkedin Url",
            "Website",
            "Company Linkedin Url",
            "Company Phone",
        ]

        original = df.reset_index(drop=True).iloc[:len(result_df)].copy()
        out = pd.DataFrame()
        for c in keep_cols:
            out[c] = original.get(c, [None] * len(original))

        # Add/overwrite enrichment columns (avoid duplicates by overwriting)
        enrichment_cols = [
            "Person Work Line",
            "Person Work Source",
            "Company Summary Line",
            "Company Summary Source",
        ]
        debug_cols = ["Debug Name Used", "Debug Author Matched", "Debug Match Score", "Debug Papers Found", "Confidence Score"]
        for col in enrichment_cols + debug_cols:
            if col in result_df.columns:
                out[col] = result_df[col].values

        combined = out

        st.subheader("Preview enriched results")
        st.dataframe(combined.head(10))

        if st.checkbox("Show debug info", value=False):
            dbg = result_df[[c for c in debug_cols if c in result_df.columns]]
            st.subheader("Debug info (per-row)")
            st.dataframe(dbg.head(10))

        csv_bytes = combined.to_csv(index=False).encode("utf-8")
        st.download_button("Download enriched CSV", data=csv_bytes, file_name="enriched_contacts.csv", mime="text/csv")
