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


# v8.1: Strong municipal anchors that MUST route to Kuntalaki
_MUNICIPAL_STRONG_ANCHORS = [
    "kunnan", "kuntakonserni", "kuntalaki", "valtuusto", "kunnanhallitus",
    "tarkastuslautakunta", "kunnanjohtaja", "kunnanvaltuusto", "kuntalain",
]

# Default keywords if cross_refs.json not available
_DEFAULT_KEYWORDS: dict[str, list[str]] = {
    "kuntalaki_410_2015": [
        "kunta", "kunnan", "valtuusto", "kunnanhallitus", "kunnanjohtaja",
        "kriisikunta", "arviointimenettely", "kuntayhtymä", "konserni",
        "kuntakonserni", "kuntalaki", "tarkastuslautakunta", "kuntalain",
        "kuntien", "kuntalainen", "kunnanvaltuusto",
    ],
    "kirjanpitolaki_1336_1997": [
        "tase", "liitetiedot", "tuloslaskelma", "poistot", "arvostus",
        "kirjanpito", "tilivuosi", "tilikausi", "kirjanpitovelvollinen",
    ],
    "kirjanpitoasetus_1339_1997": [
        "kirjanpitoasetus", "tasekaava", "tuloslaskelmakaava", "liitetieto",
        "esittämistapa", "erittely", "tase-erittelyt", "konsernitase",
        "konsernituloslaskelma", "rahoituslaskelma", "rahavirta", "kassavirta",
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
    if "kpa" in query_lower or "kirjanpitoasetus" in query_lower:
        return "kirjanpitoasetus_1339_1997"
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
        r"1339/1997": "kirjanpitoasetus_1339_1997",
        r"1141/2015": "tilintarkastuslaki_1141_2015",
        r"1397/2016": "hankintalaki_1397_2016",
        r"624/2006": "osakeyhtiolaki_624_2006",
    }
    for pattern, law_key in finlex_patterns.items():
        if re.search(pattern, query):
            return law_key
    
    return None


def _has_municipal_anchor(query: str) -> bool:
    """Check if query contains strong municipal anchors."""
    query_lower = query.lower()
    return any(anchor in query_lower for anchor in _MUNICIPAL_STRONG_ANCHORS)


def route_query(
    query: str,
    available_laws: Optional[list[str]] = None,
    default_law: str = "kuntalaki_410_2015",
    min_laws: int = 2,
) -> dict[str, float]:
    """
    Route a query to appropriate law indices (v8.1: hardened municipal routing).
    
    Args:
        query: User query string
        available_laws: List of law_keys that are indexed. If None, uses all.
        default_law: Default law to use if no keywords match
        min_laws: Minimum number of laws to return (v7: always at least 2)
        
    Returns:
        Dictionary of law_key -> weight (weights sum to 1.0)
    """
    if available_laws is None:
        available_laws = list(_get_router_keywords().keys())
    
    # Check for explicit law reference first
    explicit_law = _extract_explicit_law_reference(query)
    
    # v8.1: Check for strong municipal anchors
    has_municipal = _has_municipal_anchor(query)
    
    # Count keyword matches for each law
    query_lower = query.lower()
    keywords = _get_router_keywords()
    
    scores: dict[str, int] = {}
    for law_key, kw_list in keywords.items():
        if law_key not in available_laws:
            continue
        score = sum(1 for kw in kw_list if kw in query_lower)
        scores[law_key] = score
    
    # v8.1: Strong boost for Kuntalaki when municipal anchors present
    if has_municipal and "kuntalaki_410_2015" in available_laws:
        scores["kuntalaki_410_2015"] = scores.get("kuntalaki_410_2015", 0) + 3
    
    # v7: If explicit law reference, give it high weight but still include 2nd law
    if explicit_law and explicit_law in available_laws:
        weights = {explicit_law: 0.8}
        # Add second law with lower weight
        other_laws = [k for k, v in sorted(scores.items(), key=lambda x: x[1], reverse=True) 
                      if k != explicit_law]
        if other_laws:
            weights[other_laws[0]] = 0.2
        return weights
    
    # Get laws with any keyword matches
    matched_laws = {k: v for k, v in scores.items() if v > 0}
    
    # v7: Fallback prior distribution if no/few keyword matches
    FALLBACK_PRIOR = {
        "kuntalaki_410_2015": 0.40,
        "kirjanpitolaki_1336_1997": 0.15,
        "kirjanpitoasetus_1339_1997": 0.10,
        "tilintarkastuslaki_1141_2015": 0.15,
        "hankintalaki_1397_2016": 0.15,
        "osakeyhtiolaki_624_2006": 0.05,
    }
    
    if len(matched_laws) < min_laws:
        # Use fallback prior, filtered by available_laws
        weights = {}
        for law_key in available_laws:
            if law_key in matched_laws:
                # Boost matched laws
                weights[law_key] = FALLBACK_PRIOR.get(law_key, 0.1) + 0.2 * matched_laws[law_key]
            else:
                weights[law_key] = FALLBACK_PRIOR.get(law_key, 0.1)
        
        # Normalize
        total = sum(weights.values())
        weights = {k: v / total for k, v in weights.items()}
        
        # Keep only top min_laws
        sorted_laws = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        weights = dict(sorted_laws[:max(min_laws, len(matched_laws) + 1)])
        
        # Re-normalize
        total = sum(weights.values())
        weights = {k: v / total for k, v in weights.items()}
        
        return weights
    
    # Normal case: multiple keyword matches
    # Normalize to weights summing to 1.0
    total = sum(matched_laws.values())
    weights = {law_key: count / total for law_key, count in matched_laws.items()}
    
    # v7: Ensure at least min_laws are included
    if len(weights) < min_laws:
        # Add more laws from fallback prior
        for law_key in available_laws:
            if law_key not in weights:
                weights[law_key] = 0.1
                if len(weights) >= min_laws:
                    break
        
        # Re-normalize
        total = sum(weights.values())
        weights = {k: v / total for k, v in weights.items()}
    
    # v8.1: Force Kuntalaki into top-2 when municipal anchors present
    if has_municipal and "kuntalaki_410_2015" in available_laws:
        if "kuntalaki_410_2015" not in weights:
            # Add Kuntalaki with high weight
            weights["kuntalaki_410_2015"] = 0.5
            # Re-normalize
            total = sum(weights.values())
            weights = {k: v / total for k, v in weights.items()}
        else:
            # Ensure it's in top-2
            sorted_laws = sorted(weights.items(), key=lambda x: x[1], reverse=True)
            if sorted_laws[0][0] != "kuntalaki_410_2015" and \
               (len(sorted_laws) < 2 or sorted_laws[1][0] != "kuntalaki_410_2015"):
                # Boost Kuntalaki
                weights["kuntalaki_410_2015"] = max(weights["kuntalaki_410_2015"], sorted_laws[0][1] * 0.9)
                # Re-normalize
                total = sum(weights.values())
                weights = {k: v / total for k, v in weights.items()}
    
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

