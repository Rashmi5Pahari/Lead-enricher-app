import time
import requests
from typing import Optional, List, Dict
from .cache_utils import disk_cache_get, disk_cache_set

DEFAULT_HEADERS = {"User-Agent": "lead-enricher/1.0"}

def request_with_retries(url: str, params: dict = None, headers: dict = None, retries: int = 3, backoff: float = 1.0, timeout: int = 10):
    headers = {**DEFAULT_HEADERS, **(headers or {})}
    attempt = 0
    while attempt < retries:
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            if resp.status_code == 429:
                # rate limited
                time.sleep(backoff * (attempt + 1))
                attempt += 1
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            time.sleep(backoff * (attempt + 1))
            attempt += 1
    return None


def request_html_with_retries(url: str, headers: dict = None, retries: int = 3, backoff: float = 1.0, timeout: int = 10):
    headers = {**DEFAULT_HEADERS, **(headers or {})}
    attempt = 0
    while attempt < retries:
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            if resp.status_code == 429:
                time.sleep(backoff * (attempt + 1))
                attempt += 1
                continue
            resp.raise_for_status()
            return resp.text
        except requests.RequestException:
            time.sleep(backoff * (attempt + 1))
            attempt += 1
    return None


class OpenAlexClient:
    BASE = "https://api.openalex.org"

    def search_authors(self, name: str, per_page: int = 5) -> Optional[List[Dict]]:
        key = f"openalex:authors:{name}:{per_page}"
        cached = disk_cache_get(key)
        if cached is not None:
            return cached
        url = f"{self.BASE}/authors"
        params = {"filter": f"display_name.search:{name}", "per-page": per_page}
        data = request_with_retries(url, params=params)
        results = []
        if data and "results" in data:
            for a in data["results"]:
                results.append(a)
        disk_cache_set(key, results)
        return results

    def get_author_works(self, openalex_id: str, per_page: int = 5) -> Optional[List[Dict]]:
        key = f"openalex:works:{openalex_id}:{per_page}"
        cached = disk_cache_get(key)
        if cached is not None:
            return cached
        # openalex author id is like https://openalex.org/A12345 or A12345
        identifier = openalex_id.split('/')[-1]
        url = f"{self.BASE}/works"
        params = {"filter": f"author.id:{identifier}", "per-page": per_page, "sort": "cited_by_count:desc"}
        data = request_with_retries(url, params=params)
        works = []
        if data and "results" in data:
            works = data["results"]
        disk_cache_set(key, works)
        return works


class SemanticScholarClient:
    BASE = "https://api.semanticscholar.org/graph/v1"

    def search_author(self, name: str, limit: int = 5) -> Optional[List[Dict]]:
        key = f"semanticscholar:authors:{name}:{limit}"
        cached = disk_cache_get(key)
        if cached is not None:
            return cached
        url = f"{self.BASE}/author/search"
        params = {"query": name, "limit": limit}
        data = request_with_retries(url, params=params)
        authors = []
        if data and "data" in data:
            authors = data["data"]
        disk_cache_set(key, authors)
        return authors

    def get_author_papers(self, author_id: str, limit: int = 5) -> Optional[List[Dict]]:
        key = f"semanticscholar:works:{author_id}:{limit}"
        cached = disk_cache_get(key)
        if cached is not None:
            return cached
        # fields: title,year,externalIds
        url = f"{self.BASE}/author/{author_id}/papers"
        params = {"limit": limit, "fields": "paperId,title,year,externalIds,fieldsOfStudy"}
        data = request_with_retries(url, params=params)
        papers = []
        if data and "data" in data:
            papers = [p.get("paper", {}) for p in data["data"]]
        disk_cache_set(key, papers)
        return papers
