"""
Tilintarkastuslaki (TTL 1141/2015) builder.

Uses the generic law builder to process Tilintarkastuslaki XML into normalized JSON/JSONL.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from shared.utils.generic_law_builder import LawConfig, build_law


TTL_KEYWORD_TAGS: dict[str, list[str]] = {
    # Core audit concepts
    "tilintarkastaja": ["tilintarkastaja", "tarkastaja", "tarkastus"],
    "tilintarkastus": ["tilintarkastus", "tarkastus", "valvonta"],
    "tilintarkastuskertomus": ["tilintarkastuskertomus", "kertomus", "raportointi"],
    "huomautus": ["huomautus", "poikkeama", "havainto"],
    "vastuuvapaus": ["vastuuvapaus", "vastuu", "päätöksenteko"],
    
    # Auditor qualifications
    "ht-tilintarkastaja": ["HT-tilintarkastaja", "hyväksytty tilintarkastaja"],
    "kht-tilintarkastaja": ["KHT-tilintarkastaja", "keskuskauppakamari"],
    "jht-tilintarkastaja": ["JHT-tilintarkastaja", "julkishallinto"],
    "tilintarkastusyhteisö": ["tilintarkastusyhteisö", "yhteisö", "tarkastusyhteisö"],
    
    # Audit process
    "tarkastus": ["tarkastus", "tilintarkastus", "arviointi"],
    "tarkastussuunnitelma": ["tarkastussuunnitelma", "suunnitelma", "menetelmä"],
    "dokumentointi": ["dokumentointi", "työpaperit", "kirjaaminen"],
    "riippumattomuus": ["riippumattomuus", "objektiivisuus", "esteellisyys"],
    "salassapito": ["salassapito", "luottamuksellisuus", "tietosuoja"],
    
    # Reporting
    "lausunto": ["lausunto", "mielipide", "johtopäätös"],
    "mukautettu": ["mukautettu lausunto", "varauma", "kielteinen"],
    "vakiomuotoinen": ["vakiomuotoinen", "puhdas lausunto"],
    
    # Public interest entities
    "yleisen edun kannalta merkittävä": ["PIE", "yleisen edun kannalta merkittävä", "pörssiyhtiö"],
    "pörssiyhtiö": ["pörssiyhtiö", "listattu yhtiö", "PIE"],
    
    # Supervision
    "valvonta": ["valvonta", "PRH", "tilintarkastusvalvonta"],
    "kurinpito": ["kurinpito", "seuraamukset", "varoitus"],
}

TTL_CHAPTER_TAGS: dict[str, list[str]] = {
    "tilintarkastusvelvollisuus": ["tilintarkastusvelvollisuus", "velvollisuus", "pakollinen"],
    "tilintarkastajan kelpoisuus": ["kelpoisuus", "pätevyys", "hyväksyminen"],
    "tilintarkastajan tehtävät": ["tehtävät", "velvollisuudet", "tarkastus"],
    "tilintarkastuskertomus": ["tilintarkastuskertomus", "raportointi"],
    "riippumattomuus": ["riippumattomuus", "esteellisyys", "objektiivisuus"],
    "valvonta": ["valvonta", "PRH", "seuraamukset"],
    "seuraamukset": ["seuraamukset", "kurinpito", "varoitus"],
}


def main() -> None:
    """Build Tilintarkastuslaki JSON/JSONL."""
    
    config = LawConfig(
        law_key="tilintarkastuslaki_1141_2015",
        law_id="1141/2015",
        law_name="Tilintarkastuslaki",
        law_key_canonical="fi:act:1141/2015",
        finlex_url_base="https://finlex.fi/fi/laki/ajantasa/2015/20151141",
        xml_base_path=PROJECT_ROOT / "finlex_statute_consolidated" / "akn" / "fi" / "act" / "statute-consolidated" / "2015" / "1141",
        keyword_tags=TTL_KEYWORD_TAGS,
        chapter_tags=TTL_CHAPTER_TAGS,
    )
    
    output_dir = Path(__file__).parent / "analysis_layer" / "json"
    records = build_law(config, output_dir)
    
    print(f"\nTilintarkastuslaki processing complete!")
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()

