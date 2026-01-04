"""
Deterministic law router for multi-law retrieval.

Routes queries to appropriate law indices based on keyword matching.
No LLM dependency - pure rule-based routing.
"""
import json
import re
from pathlib import Path
from typing import Optional


# Load router keywords from cross_refs.json
_CROSS_REFS_PATH = Path(__file__).parent.parent / "cross_refs.json"


def _load_router_keywords() -> dict[str, list[str]]:
    """Load router keywords from cross_refs.json."""
    if _CROSS_REFS_PATH.exists():
        with open(_CROSS_REFS_PATH, encoding="utf-8") as f:
            data = json.load(f)
            return data.get("router_keywords", {})
    return {}


# Default keywords if cross_refs.json not available
_DEFAULT_KEYWORDS: dict[str, list[str]] = {
    "kuntalaki_410_2015": [
        "kunta", "kunnan", "valtuusto", "kunnanhallitus", "kunnanjohtaja",
        "kriisikunta", "arviointimenettely", "kuntayhtymä", "konserni",
    ],
    "kirjanpitolaki_1336_1997": [
        "tase", "liitetiedot", "tuloslaskelma", "poistot", "arvostus",
        "kirjanpito", "tilivuosi", "tilikausi", "kirjanpitovelvollinen",
    ],
    "tilintarkastuslaki_1141_2015": [
        "tilintarkastaja", "tilintarkastuskertomus", "huomautus",
        "vastuuvapaus", "tarkastuskertomus", "tilintarkastus",
    ],
    "hankintalaki_1397_2016": [
        "hankinta", "kilpailutus", "kynnysarvo", "tarjous", "sopimuskausi",
        "julkinen hankinta", "tarjouskilpailu", "hankintayksikkö",
    ],
    "osakeyhtiolaki_624_2006": [
        "konserniyhtiö", "osakeyhtiö", "yhtiökokous", "hallitus",
        "toimitusjohtaja", "osakepääoma", "osake", "yhtiö",
    ],
}


def _get_router_keywords() -> dict[str, list[str]]:
    """Get router keywords, preferring cross_refs.json."""
    loaded = _load_router_keywords()
    if loaded:
        # Merge with defaults, loaded takes precedence
        merged = _DEFAULT_KEYWORDS.copy()
        merged.update(loaded)
        return merged
    return _DEFAULT_KEYWORDS


def _extract_explicit_law_reference(query: str) -> Optional[str]:
    """
    Extract explicit law reference from query.
    
    Examples:
        "KPL 3:1" -> "kirjanpitolaki_1336_1997"
        "Kuntalaki 110 §" -> "kuntalaki_410_2015"
        "410/2015" -> "kuntalaki_410_2015"
    """
    query_lower = query.lower()
    
    # Check for law abbreviations
    if "kpl" in query_lower or "kirjanpitolaki" in query_lower:
        return "kirjanpitolaki_1336_1997"
    if "oyl" in query_lower or "osakeyhtiölaki" in query_lower:
        return "osakeyhtiolaki_624_2006"
    if "kuntalaki" in query_lower or "kuntl" in query_lower:
        return "kuntalaki_410_2015"
    if "tilintarkastuslaki" in query_lower or "ttl" in query_lower:
        return "tilintarkastuslaki_1141_2015"
    if "hankintalaki" in query_lower or "julkisista hankinnoista" in query_lower:
        return "hankintalaki_1397_2016"
    
    # Check for Finlex ID patterns
    finlex_patterns = {
        r"410/2015": "kuntalaki_410_2015",
        r"1336/1997": "kirjanpitolaki_1336_1997",
        r"1141/2015": "tilintarkastuslaki_1141_2015",
        r"1397/2016": "hankintalaki_1397_2016",
        r"624/2006": "osakeyhtiolaki_624_2006",
    }
    for pattern, law_key in finlex_patterns.items():
        if re.search(pattern, query):
            return law_key
    
    return None


def route_query(
    query: str,
    available_laws: Optional[list[str]] = None,
    default_law: str = "kuntalaki_410_2015",
) -> dict[str, float]:
    """
    Route a query to appropriate law indices.
    
    Args:
        query: User query string
        available_laws: List of law_keys that are indexed. If None, uses all.
        default_law: Default law to use if no keywords match
        
    Returns:
        Dictionary of law_key -> weight (weights sum to 1.0)
    """
    if available_laws is None:
        available_laws = list(_get_router_keywords().keys())
    
    # Check for explicit law reference first
    explicit_law = _extract_explicit_law_reference(query)
    if explicit_law and explicit_law in available_laws:
        return {explicit_law: 1.0}
    
    # Count keyword matches for each law
    query_lower = query.lower()
    keywords = _get_router_keywords()
    
    scores: dict[str, int] = {}
    for law_key, kw_list in keywords.items():
        if law_key not in available_laws:
            continue
        score = sum(1 for kw in kw_list if kw in query_lower)
        if score > 0:
            scores[law_key] = score
    
    # If no keywords matched, use default
    if not scores:
        if default_law in available_laws:
            return {default_law: 1.0}
        return {available_laws[0]: 1.0}
    
    # Normalize to weights summing to 1.0
    total = sum(scores.values())
    weights = {law_key: count / total for law_key, count in scores.items()}
    
    return weights


def calculate_k_per_law(
    weights: dict[str, float],
    total_k: int,
    min_k: int = 1,
) -> dict[str, int]:
    """
    Calculate how many results to fetch from each law index.
    
    Args:
        weights: Law weights from route_query
        total_k: Total number of results to return
        min_k: Minimum results per law (if weight > 0)
        
    Returns:
        Dictionary of law_key -> k value
    """
    import math
    
    k_per_law: dict[str, int] = {}
    for law_key, weight in weights.items():
        k = max(min_k, math.ceil(total_k * weight))
        k_per_law[law_key] = k
    
    return k_per_law


if __name__ == "__main__":
    # Test routing
    test_queries = [
        "kunnan talousarvion alijäämä",
        "tilinpäätöksen liitetiedot ja tase",
        "tilintarkastajan huomautus",
        "julkisen hankinnan kynnysarvo",
        "osakeyhtiön hallituksen vastuu",
        "KPL 3:1 liitetiedot",
        "410/2015 110 §",
    ]
    
    for q in test_queries:
        result = route_query(q)
        print(f"Query: {q}")
        print(f"  Routes: {result}")
        print()

