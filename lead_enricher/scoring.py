from rapidfuzz import fuzz

def name_match_score(a: str, b: str) -> int:
    if not a or not b:
        return 0
    return int(fuzz.token_sort_ratio(a, b))

def confidence_label(score: int, threshold_high: int = 85, threshold_med: int = 65) -> str:
    if score >= threshold_high:
        return "High"
    if score >= threshold_med:
        return "Medium"
    return "Low"
