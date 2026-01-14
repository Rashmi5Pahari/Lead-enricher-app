import pandas as pd
import time
import re
from typing import Dict, Any
from html import unescape
from .apis import OpenAlexClient, SemanticScholarClient, request_html_with_retries
from .scoring import name_match_score, confidence_label
from .cache_utils import disk_cache_get, disk_cache_set

oa = OpenAlexClient()
ss = SemanticScholarClient()

@pd.api.extensions.register_dataframe_accessor("enricher")
class EnricherAccessor:
    def __init__(self, pandas_obj):
        self._df = pandas_obj


def _gen_hook(name: str, top_title: str) -> str:
    if top_title:
        return f"I enjoyed your recent work, \"{top_title}\", and thought it connects to [our product/idea]."
    if name:
        return f"I enjoyed learning about your work, {name}."
    return "I enjoyed your recent work."

def enrich_row(row: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
    # read Apollo-style columns and build search name
    first = (row.get("First Name") or row.get("first_name") or row.get("firstName") or "").strip()
    last = (row.get("Last Name") or row.get("last_name") or row.get("lastName") or "").strip()
    company = (row.get("Company Name") or row.get("company") or row.get("company_name") or "").strip()
    website = (row.get("Website") or row.get("website") or "").strip()
    full_name_field = row.get("full_name") or row.get("Full Name")
    name = (full_name_field or f"{first} {last}".strip()).strip()

    cache_key = f"enrich:{name}:{company}:{settings.get('num_papers')}"
    cached = disk_cache_get(cache_key)
    if cached is not None:
        return {**row, **cached}

    # try OpenAlex
    authors = oa.search_authors(name, per_page=5) or []
    best_author = None
    best_score = 0
    for a in authors:
        cand_name = a.get("display_name")
        s = name_match_score(name, cand_name)
        if s > best_score:
            best_score = s
            best_author = ("openalex", a)

    # fallback semantic scholar
    if best_author is None or best_score < settings.get("match_score_threshold", 60):
        ssa = ss.search_author(name, limit=5) or []
        for a in ssa:
            cand_name = a.get("name")
            s = name_match_score(name, cand_name)
            if s > best_score:
                best_score = s
                best_author = ("semanticscholar", a)

    top_title = None
    top_year = None
    topics = []
    matched_info = ""
    debug_author_matched = False
    debug_papers_found = False

    if best_author:
        src, a = best_author
        if src == "openalex":
            author_id = a.get("id")
            affs = ", ".join([x.get("display_name","") for x in a.get("x_concepts", []) if x]) if a.get("x_concepts") else ", ".join([aff.get("display_name","") for aff in a.get("institutions", [])])
            matched_info = f"OpenAlex | {a.get('display_name')} | {affs}"
            works = oa.get_author_works(author_id, per_page=settings.get("num_papers", 5)) or []
            if works:
                w = works[0]
                top_title = w.get("title")
                top_year = w.get("display_date") or w.get("publication_year")
                # topics
                concepts = [c.get("display_name") for c in w.get("concepts", []) if c.get("display_name")] if w.get("concepts") else []
                topics = concepts
                debug_papers_found = True
            debug_author_matched = True
        else:
            author_id = a.get("authorId") or a.get("id")
            matched_info = f"SemanticScholar | {a.get('name')}"
            papers = ss.get_author_papers(author_id, limit=settings.get("num_papers", 5)) or []
            if papers:
                w = papers[0]
                top_title = w.get("title")
                top_year = w.get("year")
                topics = w.get("fieldsOfStudy") or []
                debug_papers_found = True
            debug_author_matched = True

    confidence = confidence_label(best_score, threshold_high=85, threshold_med=65)
    hook = _gen_hook(name, top_title)

    # Person Work Line: only write when author matched with sufficient score
    person_work_line = ""
    person_work_source = "none"
    threshold = settings.get("match_score_threshold", 60)
    if best_author and best_score >= threshold and (top_title or topics):
        parts = []
        if top_title:
            parts.append(f'"{top_title}"')
        if topics:
            if isinstance(topics, list):
                parts.append(', '.join(topics[:3]))
            else:
                parts.append(str(topics))
        if parts:
            person_work_line = f"{name} works on {', '.join(parts)}."
            person_work_source = "papers"

    # Company Summary Line: attempt to fetch meta description/title/h1 from website
    company_summary = ""
    company_summary_source = "none"
    if website:
        html = request_html_with_retries(website)
        if html:
            # try meta description, og:description, title, then first h1
            meta = re.search(r'<meta[^>]+name=[\"\']description[\"\'][^>]*content=[\"\']([^\"\']+)[\"\']', html, flags=re.I)
            if not meta:
                meta = re.search(r'<meta[^>]+property=[\"\']og:description[\"\'][^>]*content=[\"\']([^\"\']+)[\"\']', html, flags=re.I)
            if meta:
                company_summary = unescape(meta.group(1).strip())
                company_summary_source = "website"
            else:
                title = re.search(r'<title>([^<]+)</title>', html, flags=re.I)
                if title:
                    company_summary = unescape(title.group(1).strip())
                    company_summary_source = "website"
                else:
                    h1 = re.search(r'<h1[^>]*>([^<]+)</h1>', html, flags=re.I)
                    if h1:
                        company_summary = unescape(h1.group(1).strip())
                        company_summary_source = "website"

    out = {
        "Personalization Hook": hook,
        "Top Paper Title": top_title,
        "Top Paper Year/Date": top_year,
        "Topics": ", ".join(topics) if isinstance(topics, list) else topics,
        "Matched Author Source/Name/Affiliations": matched_info,
        "Confidence Score": confidence,
        "Hook Source": "Internal",
        # new fields
        "Person Work Line": person_work_line,
        "Person Work Source": person_work_source,
        "Company Summary Line": company_summary,
        "Company Summary Source": company_summary_source,
        # debug fields for UI
        "Debug Name Used": name,
        "Debug Author Matched": bool(debug_author_matched),
        "Debug Match Score": best_score,
        "Debug Papers Found": bool(debug_papers_found),
    }

    disk_cache_set(cache_key, out)
    return {**row, **out}

def enrich_contacts(df, settings: Dict[str, Any]):
    rows = []
    max_rows = min(len(df), settings.get("max_rows", 50))
    for i in range(max_rows):
        row = df.iloc[i].to_dict()
        enriched = enrich_row(row, settings)
        rows.append(enriched)
        # light rate limiting
        time.sleep(settings.get("per_row_delay", 0.5))
    return pd.DataFrame(rows)
