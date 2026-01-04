"""
Osakeyhtiölaki (OYL 624/2006) builder.

Rajattu: kuntakonsernin Oy:t (hallinto, vastuut).
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from shared.utils.generic_law_builder import LawConfig, build_law


OYL_KEYWORD_TAGS: dict[str, list[str]] = {
    # Company structure
    "osakeyhtiö": ["osakeyhtiö", "yhtiö", "oy"],
    "osakepääoma": ["osakepääoma", "pääoma", "perustaminen"],
    "osake": ["osake", "osakekirja", "omistus"],
    "osakkeenomistaja": ["osakkeenomistaja", "omistaja", "osakas"],
    
    # Governance
    "yhtiökokous": ["yhtiökokous", "kokous", "päätöksenteko"],
    "hallitus": ["hallitus", "johtaminen", "päätöksenteko"],
    "toimitusjohtaja": ["toimitusjohtaja", "TJ", "johto"],
    "hallintoneuvosto": ["hallintoneuvosto", "valvonta"],
    
    # Liability and duties
    "huolellisuusvelvollisuus": ["huolellisuusvelvollisuus", "vastuu", "johdon vastuu"],
    "lojaliteettivelvollisuus": ["lojaliteettivelvollisuus", "yhtiön etu"],
    "vahingonkorvaus": ["vahingonkorvaus", "vastuu", "korvaus"],
    
    # Financial matters
    "tilinpäätös": ["tilinpäätös", "kirjanpito", "raportointi"],
    "voitonjako": ["voitonjako", "osinko", "varojen jako"],
    "osinko": ["osinko", "voitonjako", "jako"],
    "pääomalaina": ["pääomalaina", "rahoitus", "laina"],
    "oman pääoman menettäminen": ["oman pääoman menettäminen", "kriisi", "ilmoitus"],
    
    # Group structures
    "konserni": ["konserni", "kuntakonserni", "tytäryhtiö"],
    "emoyhtiö": ["emoyhtiö", "omistaja", "konserni"],
    "tytäryhtiö": ["tytäryhtiö", "omistettu", "konserni"],
    "konsernitilinpäätös": ["konsernitilinpäätös", "konsernilaskelma"],
    
    # Structural changes
    "sulautuminen": ["sulautuminen", "fuusio", "yhdistyminen"],
    "jakautuminen": ["jakautuminen", "jako"],
    "selvitystila": ["selvitystila", "purkaminen", "lopettaminen"],
    "konkurssi": ["konkurssi", "maksukyvyttömyys"],
    
    # Auditing
    "tilintarkastus": ["tilintarkastus", "tarkastus"],
    "tilintarkastaja": ["tilintarkastaja", "tarkastaja"],
}

OYL_CHAPTER_TAGS: dict[str, list[str]] = {
    "osakeyhtiön perustaminen": ["perustaminen", "rekisteröinti"],
    "hallinto": ["hallinto", "hallitus", "yhtiökokous", "toimitusjohtaja"],
    "yhtiökokous": ["yhtiökokous", "päätöksenteko", "äänestysoikeus"],
    "hallitus": ["hallitus", "jäsenet", "tehtävät"],
    "tilinpäätös": ["tilinpäätös", "toimintakertomus", "raportointi"],
    "varojen jako": ["varojen jako", "voitonjako", "osinko"],
    "pääoma": ["osakepääoma", "pääoma", "korottaminen", "alentaminen"],
    "oma pääoma": ["oma pääoma", "sidottu", "vapaa"],
    "sulautuminen": ["sulautuminen", "fuusio"],
    "jakautuminen": ["jakautuminen", "jako"],
    "vahingonkorvaus": ["vahingonkorvaus", "vastuu"],
}


def main() -> None:
    """Build Osakeyhtiölaki JSON/JSONL."""
    
    config = LawConfig(
        law_key="osakeyhtiolaki_624_2006",
        law_id="624/2006",
        law_name="Osakeyhtiölaki",
        law_key_canonical="fi:act:624/2006",
        finlex_url_base="https://finlex.fi/fi/laki/ajantasa/2006/20060624",
        xml_base_path=PROJECT_ROOT / "finlex_statute_consolidated" / "akn" / "fi" / "act" / "statute-consolidated" / "2006" / "624",
        keyword_tags=OYL_KEYWORD_TAGS,
        chapter_tags=OYL_CHAPTER_TAGS,
    )
    
    output_dir = Path(__file__).parent / "analysis_layer" / "json"
    records = build_law(config, output_dir)
    
    print(f"\nOsakeyhtiölaki processing complete!")
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()

