"""
Hankintalaki (1397/2016) builder.

Laki julkisista hankinnoista ja käyttöoikeussopimuksista.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from shared.utils.generic_law_builder import LawConfig, build_law


HANK_KEYWORD_TAGS: dict[str, list[str]] = {
    # Core procurement concepts
    "hankinta": ["hankinta", "julkinen hankinta", "kilpailutus"],
    "hankintayksikkö": ["hankintayksikkö", "ostaja", "tilaaja"],
    "tarjouspyyntö": ["tarjouspyyntö", "kilpailutus", "ilmoitus"],
    "tarjous": ["tarjous", "tarjoaja", "kilpailutus"],
    
    # Thresholds
    "kynnysarvo": ["kynnysarvo", "raja-arvo", "soveltamisala"],
    "kansallinen kynnysarvo": ["kansallinen kynnysarvo", "kotimainen"],
    "eu-kynnysarvo": ["EU-kynnysarvo", "eurooppalainen", "unionin laajuinen"],
    
    # Contract types
    "tavarahankinta": ["tavarahankinta", "tavara", "tuote"],
    "palveluhankinta": ["palveluhankinta", "palvelu", "toimeksianto"],
    "rakennusurakka": ["rakennusurakka", "urakka", "rakentaminen"],
    "käyttöoikeussopimus": ["käyttöoikeussopimus", "konsessio"],
    
    # Procedures
    "avoin menettely": ["avoin menettely", "menettelytapa"],
    "rajoitettu menettely": ["rajoitettu menettely", "esikarsinta"],
    "neuvottelumenettely": ["neuvottelumenettely", "neuvottelu"],
    "suorahankinta": ["suorahankinta", "poikkeus", "kilpailuttamatta"],
    
    # Selection and award
    "soveltuvuus": ["soveltuvuus", "kelpoisuus", "poissulkeminen"],
    "valintaperuste": ["valintaperuste", "vertailu", "pisteytys"],
    "kokonaistaloudellinen edullisuus": ["kokonaistaloudellinen edullisuus", "paras hinta-laatusuhde"],
    "halvin hinta": ["halvin hinta", "hinta"],
    
    # Legal remedies
    "hankintaoikaisu": ["hankintaoikaisu", "muutoksenhaku", "oikaisu"],
    "valitus": ["valitus", "markkinaoikeus", "muutoksenhaku"],
    "markkinaoikeus": ["markkinaoikeus", "valitus", "oikeussuoja"],
    
    # Contracts
    "hankintasopimus": ["hankintasopimus", "sopimus", "sopimuskausi"],
    "puitejärjestely": ["puitejärjestely", "puitesopimus"],
    "dynaaminen hankintajärjestelmä": ["dynaaminen hankintajärjestelmä", "DPS"],
}

HANK_CHAPTER_TAGS: dict[str, list[str]] = {
    "soveltamisala": ["soveltamisala", "kynnysarvot", "poikkeukset"],
    "hankintamenettelyt": ["hankintamenettelyt", "kilpailutus"],
    "tarjouspyyntö": ["tarjouspyyntö", "ilmoittaminen"],
    "tarjousten käsittely": ["tarjousten käsittely", "vertailu", "valinta"],
    "oikeussuoja": ["oikeussuoja", "muutoksenhaku", "markkinaoikeus"],
}


def main() -> None:
    """Build Hankintalaki JSON/JSONL."""
    
    config = LawConfig(
        law_key="hankintalaki_1397_2016",
        law_id="1397/2016",
        law_name="Laki julkisista hankinnoista ja käyttöoikeussopimuksista",
        law_key_canonical="fi:act:1397/2016",
        finlex_url_base="https://finlex.fi/fi/laki/ajantasa/2016/20161397",
        xml_base_path=PROJECT_ROOT / "finlex_statute_consolidated" / "akn" / "fi" / "act" / "statute-consolidated" / "2016" / "1397",
        keyword_tags=HANK_KEYWORD_TAGS,
        chapter_tags=HANK_CHAPTER_TAGS,
    )
    
    output_dir = Path(__file__).parent / "analysis_layer" / "json"
    records = build_law(config, output_dir)
    
    print(f"\nHankintalaki processing complete!")
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()

