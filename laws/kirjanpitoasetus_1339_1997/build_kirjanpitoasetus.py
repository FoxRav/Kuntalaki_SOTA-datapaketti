"""
Kirjanpitoasetus (KPA 1339/1997) builder.

Uses the generic law builder to process Kirjanpitoasetus XML into normalized JSON/JSONL.
KPA täydentää Kirjanpitolakia liitetietojen ja esittämistapojen osalta.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from shared.utils.generic_law_builder import LawConfig, build_law


KPA_KEYWORD_TAGS: dict[str, list[str]] = {
    # Balance sheet / Tase
    "tase": ["tase", "vastaavaa", "vastattavaa", "taseen"],
    "pysyvät vastaavat": ["pysyvät vastaavat", "käyttöomaisuus", "aineettomat"],
    "vaihtuvat vastaavat": ["vaihtuvat vastaavat", "vaihto-omaisuus", "saamiset"],
    "oma pääoma": ["oma pääoma", "osakepääoma", "ylikurssi", "rahasto"],
    "vieras pääoma": ["vieras pääoma", "velat", "laina"],
    
    # Income statement / Tuloslaskelma
    "tuloslaskelma": ["tuloslaskelma", "tulos", "tilikauden tulos"],
    "liikevaihto": ["liikevaihto", "myyntituotot", "tuotot"],
    "liiketoiminnan muut tuotot": ["liiketoiminnan muut tuotot", "muut tuotot"],
    "materiaalit ja palvelut": ["materiaalit", "palvelut", "aineet", "tarvikkeet"],
    "henkilöstökulut": ["henkilöstökulut", "palkat", "sosiaalikulut", "eläke"],
    "poistot": ["poistot", "arvonalentumiset", "arvonalentuminen"],
    "rahoitustuotot ja -kulut": ["rahoitustuotot", "rahoituskulut", "korkokulut", "korkotuotot"],
    "satunnaiset erät": ["satunnaiset erät", "satunnaiset tuotot", "satunnaiset kulut"],
    "tilinpäätössiirrot": ["tilinpäätössiirrot", "poistoero", "vapaaehtoiset varaukset"],
    
    # Notes / Liitetiedot
    "liitetiedot": ["liitetiedot", "liitetieto", "liitteet"],
    "tilinpäätöksen laatimisperiaatteet": ["laatimisperiaatteet", "arvostusperiaatteet", "jaksotusperiaatteet"],
    "tuloslaskelmaa koskevat liitetiedot": ["tuloslaskelman liitetiedot"],
    "tasetta koskevat liitetiedot": ["taseen liitetiedot", "tase-erittelyt"],
    "vakuudet ja vastuusitoumukset": ["vakuudet", "vastuusitoumukset", "pantti", "takaus"],
    "henkilöstö": ["henkilöstö", "henkilömäärä", "keskimääräinen"],
    "toimintakertomus": ["toimintakertomus", "olennaiset tapahtumat"],
    
    # Consolidated / Konserni
    "konsernitilinpäätös": ["konsernitilinpäätös", "konserni", "konsernin"],
    "konsernituloslaskelma": ["konsernituloslaskelma"],
    "konsernitase": ["konsernitase"],
    "eliminoinnit": ["eliminoinnit", "sisäiset erät", "konsernin sisäinen"],
    
    # Cash flow / Rahoituslaskelma
    "rahoituslaskelma": ["rahoituslaskelma", "kassavirta", "rahavirta"],
    "liiketoiminnan rahavirta": ["liiketoiminnan rahavirta"],
    "investointien rahavirta": ["investointien rahavirta"],
    "rahoituksen rahavirta": ["rahoituksen rahavirta"],
    
    # Valuation / Arvostus
    "arvostus": ["arvostus", "arvostaminen", "kirjanpitoarvo"],
    "hankintameno": ["hankintameno", "hankintahinta"],
    "käypä arvo": ["käypä arvo", "markkina-arvo"],
    
    # Small entities / Pienyritys
    "pienyritys": ["pienyritys", "mikroyritys", "pieni kirjanpitovelvollinen"],
    "helpotukset": ["helpotukset", "kevennykset", "poikkeukset"],
}

KPA_CHAPTER_TAGS: dict[str, list[str]] = {
    "tuloslaskelma": ["tuloslaskelma", "tulos", "tuotot", "kulut"],
    "tase": ["tase", "vastaavaa", "vastattavaa", "oma pääoma", "vieras pääoma"],
    "liitetiedot": ["liitetiedot", "liitetieto", "lisätiedot"],
    "konsernitilinpäätös": ["konsernitilinpäätös", "konserni", "konsernin"],
    "rahoituslaskelma": ["rahoituslaskelma", "kassavirta", "rahavirta"],
    "erityissäännökset": ["erityissäännökset", "poikkeukset", "erikoistapaukset"],
}


def main() -> None:
    """Build Kirjanpitoasetus JSON/JSONL."""
    
    config = LawConfig(
        law_key="kirjanpitoasetus_1339_1997",
        law_id="1339/1997",
        law_name="Kirjanpitoasetus",
        law_key_canonical="fi:act:1339/1997",
        finlex_url_base="https://finlex.fi/fi/laki/ajantasa/1997/19971339",
        xml_base_path=PROJECT_ROOT / "finlex_statute_consolidated" / "akn" / "fi" / "act" / "statute-consolidated" / "1997" / "1339",
        keyword_tags=KPA_KEYWORD_TAGS,
        chapter_tags=KPA_CHAPTER_TAGS,
    )
    
    output_dir = Path(__file__).parent / "analysis_layer" / "json"
    records = build_law(config, output_dir)
    
    print(f"\nKirjanpitoasetus processing complete!")
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()

