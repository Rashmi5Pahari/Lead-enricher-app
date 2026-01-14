import os
import json
import hashlib
from typing import Optional

CACHE_DIR = os.path.join(os.getcwd(), ".cache", "lead_enricher")

def ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)

def _key_to_path(key: str) -> str:
    ensure_cache_dir()
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return os.path.join(CACHE_DIR, f"{h}.json")

def disk_cache_get(key: str) -> Optional[dict]:
    path = _key_to_path(key)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def disk_cache_set(key: str, value: dict):
    path = _key_to_path(key)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(value, f)
    except Exception:
        pass
