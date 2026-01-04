"""
Query-time boosting for moment-level precision.

Applies lightweight post-score boosts based on query terms.
Boost MUST NOT exceed 5% of total score.

v4: Added anchor-overlap rerank for moment disambiguation.
"""

from __future__ import annotations

import re
from typing import Any

# v4: Activation terms for anchor overlap calculation
ANCHOR_ACTIVATION_TERMS = [
    "valvonta", "riski", "riskienhallinta", "alijäämä", "kattam",
    "tuloskäsittely", "konserni", "tavoitteiden", "olennaiset",
]

# v4: Sections that use anchor overlap
ANCHOR_SECTIONS = {"115", "110", "110a", "113", "114", "62", "62a", "62b", "118"}

# Query term to (section_id, moment, boost) mappings
# If query contains any of the terms, boost the specific section/moment
BOOST_RULES: list[tuple[list[str], str, str | None, float]] = [
    # §115 moment disambiguation - VERIFIED against actual content
    # 115:1 - tavoitteet, olennaiset tapahtumat, SISÄINEN VALVONTA, RISKIENHALLINTA
    (
        ["tavoitteiden toteutuminen", "olennaiset tapahtumat", "olennaiset asiat", 
         "tilikauden jälkeiset", "merkittävät tapahtumat", "tärkeät tapahtumat",
         "sisäinen valvonta", "sisäisen valvonnan", "riskienhallinta", "riskienhallinnan",
         "valvonta ja riskit", "kontrollit"],
        "115", "1", 0.04
    ),
    # 115:2 - alijäämäselvitys ja talouden tasapainotus (JOS taseessa alijäämää)
    (
        ["alijäämäselvitys", "alijäämän kattamissuunnitelma", "talouden tasapainotus",
         "tasapainotuksen toteutuminen", "kattamaton alijäämä", "taseen alijäämä"],
        "115", "2", 0.04
    ),
    # 115:3 - tuloksen käsittely
    (
        ["tuloksen käsittely", "tilikauden tulos", "tuloskäsittely", 
         "tuloskäsittelyesitys", "ylijäämän käyttö"],
        "115", "3", 0.04
    ),
    # Toimintakertomus general boost when explicitly mentioned
    (
        ["toimintakertomuksessa", "toimintakertomuksen"],
        "115", None, 0.03
    ),
    # §110a COVID boost + §110 penalty
    (
        ["korona", "koronaepidemia", "covid", "covid-19", "pandemia", "epidemia", "poikkeus"],
        "110a", None, 0.05
    ),
    # v4: Boost §113 when explicitly about yksittäinen kunta / ei konserni
    (
        ["yksittäisen kunnan", "ei konserni", "kunnan tilinpäätöksen asiakirjat"],
        "113", None, 0.05
    ),
    # v4: Boost §62 when explicitly about eroaminen / ei yhdistyminen
    (
        ["kuntayhtymän eroaminen", "eroaminen kuntayhtymästä", "ei yhdistyminen", "ei jakautuminen"],
        "62", None, 0.08
    ),
    # §118 moment disambiguation
    # 118:2 - alijäämän kattamatta jättäminen
    (
        ["alijäämän kattamatta", "määräajan ylitys", "kattamatta jättäminen"],
        "118", "2", 0.03
    ),
    # 118:3 - tunnuslukurajat
    (
        ["tunnusluku", "tunnusluvut", "raja-arvo", "raja-arvot", "kriteerit", "kriisikuntakriteerit"],
        "118", "3", 0.03
    ),
    # 118:5 - arviointiryhmä
    (
        ["arviointiryhmä", "ryhmän asettaminen"],
        "118", "5", 0.03
    ),
    # 118:6 - ehdotusten käsittely
    (
        ["arviointiryhmän ehdotukset", "ehdotusten käsittely"],
        "118", "6", 0.03
    ),
]

# Penalty rules: if query contains terms, LOWER score for specific sections
PENALTY_RULES: list[tuple[list[str], str, float]] = [
    # If query is about COVID, penalize §110 (not §110a)
    (
        ["korona", "koronaepidemia", "covid", "covid-19", "pandemia", "epidemia"],
        "110", -0.04
    ),
    # If query is about konserni, penalize §113 (not §114)
    (
        ["konserni", "konsernitilinpäätös", "kuntakonserni", "konsolidointi"],
        "113", -0.04
    ),
    # If query is about yksittäinen kunta tilinpäätös, penalize §114
    (
        ["yksittäisen kunnan", "ei konserni", "kunnan tilinpäätös", "yksittäinen kunta"],
        "114", -0.05
    ),
    # Talousarvio vs tilinpäätös
    (
        ["talousarvion rakenne", "talousarvion osat", "taloussuunnitelman rakenne"],
        "113", -0.04
    ),
    # Kuntayhtymä perussopimus vs eroaminen/yhdistyminen/jakautuminen
    (
        ["perussopimus", "perussopimuksen sisältö", "perussopimuksen muuttaminen"],
        "62", -0.05
    ),
    (
        ["perussopimus", "perussopimuksen sisältö", "perussopimuksen muuttaminen"],
        "62a", -0.05
    ),
    (
        ["perussopimus", "perussopimuksen sisältö", "perussopimuksen muuttaminen"],
        "62b", -0.05
    ),
    # Kuntayhtymän eroaminen vs yhdistyminen/jakautuminen
    (
        ["eroaminen", "kuntayhtymästä eroaminen", "ei yhdistyminen"],
        "62a", -0.05
    ),
    (
        ["eroaminen", "kuntayhtymästä eroaminen", "ei jakautuminen"],
        "62b", -0.05
    ),
    # Kuntayhtymien yhdistyminen vs eroaminen
    (
        ["yhdistyminen", "kuntayhtymien yhdistyminen", "ei eroaminen"],
        "62", -0.05
    ),
    (
        ["yhdistyminen", "kuntayhtymien yhdistyminen"],
        "62b", -0.03
    ),
    # Yksittäinen kunta vs konserni (vahvempi)
    (
        ["ei konserni", "yksittäisen kunnan", "yksittäinen kunta"],
        "114", -0.10
    ),
    # v4: Kuntayhtymän eroaminen penalty for 62a/62b
    (
        ["kuntayhtymän eroaminen", "eroaminen kuntayhtymästä", "ei yhdistyminen", "ei jakautuminen"],
        "62a", -0.10
    ),
    (
        ["kuntayhtymän eroaminen", "eroaminen kuntayhtymästä", "ei yhdistyminen", "ei jakautuminen"],
        "62b", -0.10
    ),
]


def normalize_query_terms(query: str) -> set[str]:
    """Normalize query into terms for overlap matching."""
    # Lowercase, remove punctuation, split
    query_clean = re.sub(r"[^\w\s]", " ", query.lower())
    terms = set(query_clean.split())
    
    # Also add bigrams for multi-word anchors
    words = query_clean.split()
    for i in range(len(words) - 1):
        terms.add(f"{words[i]} {words[i+1]}")
    
    return terms


def calculate_anchor_overlap(query_terms: set[str], anchors: list[str]) -> int:
    """Calculate number of anchor terms that appear in query."""
    count = 0
    for anchor in anchors:
        anchor_lower = anchor.lower()
        # Check if anchor (possibly multi-word) is in query terms
        if anchor_lower in query_terms:
            count += 1
        # Also check if all words of anchor appear in query
        else:
            anchor_words = set(anchor_lower.split())
            if anchor_words and anchor_words.issubset(query_terms):
                count += 1
    return count


def should_use_anchor_overlap(query: str) -> bool:
    """Check if query contains activation terms for anchor overlap."""
    query_lower = query.lower()
    return any(term in query_lower for term in ANCHOR_ACTIVATION_TERMS)


def apply_query_boost(
    query: str,
    hits: list[dict],
    max_boost_pct: float = 0.05,
) -> list[dict]:
    """Apply query-time boosting to search results.
    
    Args:
        query: The search query
        hits: List of hit dicts with 'section_num', 'moment', 'score', optional 'anchors'
        max_boost_pct: Maximum boost as fraction of score (default 5%)
    
    Returns:
        Updated hits list with adjusted scores, re-sorted
    """
    query_lower = query.lower()
    
    # v4: Prepare query terms for anchor overlap
    use_anchor_overlap = should_use_anchor_overlap(query)
    query_terms = normalize_query_terms(query) if use_anchor_overlap else set()
    
    for hit in hits:
        section_id = str(hit.get("section_num", "")).replace(" ", "").lower()
        moment = str(hit.get("moment", "")).strip()
        original_score = float(hit.get("score", 0.0))
        
        boost = 0.0
        
        # Apply boost rules
        for terms, target_section, target_moment, boost_value in BOOST_RULES:
            # Check if any term is in the query
            term_match = any(term in query_lower for term in terms)
            if not term_match:
                continue
            
            # Check if hit matches target section/moment
            target_section_lower = target_section.lower()
            if section_id != target_section_lower:
                continue
            
            # If target_moment is None, apply to all moments of this section
            if target_moment is None or moment == target_moment:
                boost += boost_value
        
        # Apply penalty rules
        for terms, target_section, penalty_value in PENALTY_RULES:
            term_match = any(term in query_lower for term in terms)
            if not term_match:
                continue
            
            target_section_lower = target_section.lower()
            if section_id == target_section_lower:
                boost += penalty_value  # penalty_value is negative
        
        # v4: Apply anchor overlap boost
        if use_anchor_overlap and section_id in ANCHOR_SECTIONS:
            anchors = hit.get("anchors", [])
            if anchors:
                overlap_count = calculate_anchor_overlap(query_terms, anchors)
                anchor_boost = min(0.01 * overlap_count, 0.05)  # Cap at +0.05
                boost += anchor_boost
                hit["anchor_overlap"] = overlap_count
        
        # Cap boost at max_boost_pct of original score
        max_allowed = original_score * max_boost_pct
        if abs(boost) > max_allowed:
            boost = max_allowed if boost > 0 else -max_allowed
        
        # Apply boost
        new_score = original_score + boost
        # v4: Clamp to 0 if penalty drops below 0
        if new_score < 0:
            new_score = 0.0
        hit["score"] = round(new_score, 4)
        hit["boost_applied"] = round(boost, 4)
    
    # Re-sort by score descending
    hits.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    
    return hits

