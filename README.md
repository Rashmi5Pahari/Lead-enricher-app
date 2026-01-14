# lead-enricher-app
 
Simple Streamlit app to enrich Apollo contacts CSV with academic paper and author info (OpenAlex + Semantic Scholar).

Local run
1. Create and activate a Python virtualenv (optional but recommended):

```bash
python -m venv .venv
source .venv/bin/activate    # macOS / Linux
.venv\\Scripts\\activate   # Windows
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
streamlit run app.py
```

How to use
- Upload your Apollo contacts CSV (CSV columns like `full_name` or `first_name` + `last_name` help).
- Choose settings in the sidebar (number of papers, match score threshold, max rows).
- Click `Run enrichment` — progress shown.
- Preview results, then click `Download enriched CSV`.

Deployment (simple)
- You can deploy to Render or Railway by pointing to this repo and setting the start command to:

```
streamlit run app.py --server.port $PORT
```

Notes
- Results depend on name quality; the app uses OpenAlex and Semantic Scholar APIs without API keys. Respect rate limits.
- Results depend on name quality; the app uses OpenAlex and Semantic Scholar APIs without API keys. Respect rate limits.

**Deploy on Streamlit Community Cloud**

- Push this repository to GitHub and deploy using Streamlit Community Cloud (recommended for a stable public URL).

- From VS Code (example commands) — replace `<username>` and `<repo>` with your GitHub info:

```powershell
git init
git add .
git commit -m "Initial commit - lead-enricher-app"
git branch -M main
git remote add origin https://github.com/<username>/<repo>.git
git push -u origin main
```

- Deploy on Streamlit Cloud:
	1. Sign in at https://share.streamlit.io using your GitHub account.
	2. Click **New app** → choose the GitHub repo, branch `main`, and set the **Main file path** to `lead-enricher-app/app.py`.
	3. Streamlit Cloud will install dependencies from `requirements.txt` and start the app. Use the dashboard to view logs and restarts.

**Main file guidance**

- If your Streamlit app entry point is `lead-enricher-app/app.py`, set the **Main file path** exactly to `lead-enricher-app/app.py` in Streamlit Cloud. If you move the app, update this path in the deploy settings.

**Secrets**

- To keep credentials or a simple password secret, use Streamlit Cloud's Secrets (Settings → Secrets). Add a key named `APP_PASSWORD` with a strong value.
- In your app you can access this as `st.secrets["APP_PASSWORD"]` (no code changes required here unless you want to enforce auth). For example, to read it in `app.py`:

```python
import streamlit as st
pw = st.secrets.get("APP_PASSWORD")
```

**Optional / Advanced (temporary sharing or programmatic tunnels)**

- If you only need a quick, temporary public URL for testing, you can use tools like `ngrok` or `pyngrok` to tunnel a local port — this is useful for brief demos but not recommended for production.
- If you previously added a Flask API or used `ngrok`, those approaches are optional advanced workflows and not required for Streamlit Cloud deployment.

For reliable public access, prefer Streamlit Community Cloud or a hosted provider such as Render or Railway.

**Repository hygiene**

- Do not commit `.venv`; create it locally with `python -m venv .venv`.
- Do not commit contact CSVs (may contain PII). Keep exported CSVs local and out of source control.
