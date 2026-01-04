"""
Kirjanpitolaki (KPL 1336/1997) builder.

Uses the generic law builder to process Kirjanpitolaki XML into normalized JSON/JSONL.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from shared.utils.generic_law_builder import LawConfig, build_law


# Kirjanpitolaki-specific keyword tags
KPL_KEYWORD_TAGS: dict[str, list[str]] = {
    # Core accounting concepts
    "kirjanpitovelvollinen": ["kirjanpitovelvollinen", "velvollisuus", "soveltamisala"],
    "liiketapahtuma": ["liiketapahtuma", "kirjaus", "kirjanpito"],
    "tosite": ["tosite", "dokumentointi", "kirjanpito"],
    "tilikausi": ["tilikausi", "tilivuosi", "vuosijakso"],
    "tilinpäätös": ["tilinpäätös", "raportointi", "tase", "tuloslaskelma"],
    
    # Balance sheet concepts
    "tase": ["tase", "vastaavaa", "vastattavaa", "taseasema"],
    "vastaavaa": ["vastaavaa", "varat", "omaisuus", "tase"],
    "vastattavaa": ["vastattavaa", "velat", "oma pääoma", "tase"],
    "pysyvät vastaavat": ["pysyvät vastaavat", "käyttöomaisuus", "investoinnit"],
    "vaihtuvat vastaavat": ["vaihtuvat vastaavat", "vaihto-omaisuus", "saamiset"],
    
    # Income statement concepts
    "tuloslaskelma": ["tuloslaskelma", "tulos", "tuotot", "kulut"],
    "liikevaihto": ["liikevaihto", "myynti", "tuotot"],
    "kulut": ["kulut", "menot", "kustannukset"],
    
    # Valuation and depreciation
    "hankintameno": ["hankintameno", "hankintahinta", "arvostus"],
    "poisto": ["poisto", "vaikutusaika", "hankintameno"],
    "arvonkorotus": ["arvonkorotus", "käypä arvo", "arvostus"],
    "käypä arvo": ["käypä arvo", "markkina-arvo", "arvostus"],
    
    # Notes and reporting
    "liitetiedot": ["liitetiedot", "liitteet", "tilinpäätös", "raportointi"],
    "toimintakertomus": ["toimintakertomus", "raportointi", "johdon selonteko"],
    
    # Special cases
    "konserni": ["konserni", "konsernitilinpäätös", "emoyhtiö", "tytäryhtiö"],
    "pienyritys": ["pienyritys", "helpotus", "raja-arvot"],
    "mikroyritys": ["mikroyritys", "helpotus", "raja-arvot"],
    "tilintarkastus": ["tilintarkastus", "tarkastus", "valvonta"],
    
    # Archiving
    "säilyttäminen": ["säilyttäminen", "arkistointi", "dokumentointi"],
    "aineisto": ["aineisto", "kirjanpitoaineisto", "dokumentointi"],
}

# Kirjanpitolaki chapter-based tags
KPL_CHAPTER_TAGS: dict[str, list[str]] = {
    "kirjanpitovelvollisuus": ["kirjanpitovelvollisuus", "soveltamisala"],
    "liiketapahtum": ["liiketapahtuma", "kirjaus", "kirjaaminen"],
    "tilinpäätö": ["tilinpäätös", "tase", "tuloslaskelma", "raportointi"],
    "tilinpäätöksen": ["tilinpäätös", "tase", "tuloslaskelma", "raportointi"],
    "arvostus": ["arvostus", "hankintameno", "käypä arvo"],
    "konsernitilinpäätös": ["konserni", "konsernitilinpäätös", "yhdistely"],
    "kansainvälis": ["IFRS", "kansainvälinen", "tilinpäätös"],
    "tilinpäätöksen julkistaminen": ["julkistaminen", "rekisteröinti", "raportointi"],
    "kirjanpitoaineisto": ["aineisto", "säilyttäminen", "arkistointi"],
    "erinäis": ["erinäinen", "määritelmät"],
}

# Moment-specific disambiguation (will be expanded as we learn the structure)
KPL_MOMENT_SPECIFIC_TAGS: dict[str, dict[str, list[str]]] = {
    # Chapter 3 - Tilinpäätös
    "1": {
        "default": ["tilinpäätöksen sisältö", "tilinpäätöksen osat"],
    },
    # Chapter 4 - Tilinpäätöserät
    "2": {
        "default": ["taseen kaava", "taseen rakenne"],
    },
    "3": {
        "default": ["tuloslaskelman kaava", "tuloslaskelman rakenne"],
    },
    # Chapter 5 - Arvostus ja jaksotus
    "5": {
        "default": ["arvostusperiaatteet", "hankintameno"],
    },
    "11": {
        "default": ["poistosuunnitelma", "suunnitelman mukaiset poistot"],
    },
}

# Moment-specific anchors
KPL_MOMENT_ANCHORS: dict[str, dict[str, list[str]]] = {
    # Key sections that need disambiguation
    "3": {  # Tilinpäätöksen sisältö
        "default": ["tilinpäätös", "tase", "tuloslaskelma", "liitetiedot"],
    },
    "5": {  # Arvostus
        "default": ["hankintameno", "arvostus", "jaksotus"],
    },
    "11": {  # Poistot
        "default": ["poisto", "vaikutusaika", "suunnitelma"],
    },
}


def main() -> None:
    """Build Kirjanpitolaki JSON/JSONL."""
    
    # Configuration for Kirjanpitolaki
    config = LawConfig(
        law_key="kirjanpitolaki_1336_1997",
        law_id="1336/1997",
        law_name="Kirjanpitolaki",
        law_key_canonical="fi:act:1336/1997",
        finlex_url_base="https://finlex.fi/fi/laki/ajantasa/1997/19971336",
        xml_base_path=PROJECT_ROOT / "finlex_statute_consolidated" / "akn" / "fi" / "act" / "statute-consolidated" / "1997" / "1336",
        keyword_tags=KPL_KEYWORD_TAGS,
        chapter_tags=KPL_CHAPTER_TAGS,
        moment_specific_tags=KPL_MOMENT_SPECIFIC_TAGS,
        moment_anchors=KPL_MOMENT_ANCHORS,
    )
    
    # Output directory
    output_dir = Path(__file__).parent / "analysis_layer" / "json"
    
    # Build the law
    records = build_law(config, output_dir)
    
    print(f"\nKirjanpitolaki processing complete!")
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()

