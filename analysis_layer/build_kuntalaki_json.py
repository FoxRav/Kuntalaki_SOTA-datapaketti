"""
Kuntalaki AKN XML → Normalisoitu JSON -muunnos.

Tuottaa SOTA-tasoisen analyysidatan, jossa jokainen momentti on omana tietueena.
Sisältää automaattisen semanttisen tagituksen.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from lxml import etree

# Semantic tag mappings based on chapter titles and keywords
CHAPTER_TAGS: dict[str, list[str]] = {
    "talous": ["talous", "budjetti", "rahoitus"],
    "talousarvio": ["talousarvio", "budjetti", "investoinnit"],
    "kirjanpito": ["kirjanpito", "tilinpäätös", "laskentatoimi"],
    "tarkastus": ["tarkastus", "tilintarkastus", "valvonta"],
    "hallinto": ["hallinto", "organisaatio", "johtaminen"],
    "päätöksenteko": ["päätöksenteko", "toimivalta", "delegointi"],
    "valtuusto": ["valtuusto", "demokratia", "päätöksenteko"],
    "kuntayhtymä": ["kuntayhtymä", "yhteistoiminta", "kuntaliitos"],
    "konserni": ["kuntakonserni", "tytäryhteisö", "omistajaohjaus"],
    "osallistuminen": ["osallistuminen", "vaikuttaminen", "demokratia"],
    "luottamushenkilö": ["luottamushenkilö", "valtuutettu", "palkkio"],
    "viranomainen": ["viranomainen", "viranhaltija", "henkilöstö"],
}

KEYWORD_TAGS: dict[str, list[str]] = {
    "alijäämä": ["alijäämä", "talousriski", "kriisikunta"],
    "ylijäämä": ["ylijäämä", "talous"],
    "laina": ["laina", "velka", "rahoitus"],
    "takaus": ["takaus", "vakuus", "rahoitus"],
    "investointi": ["investointi", "hanke", "talous"],
    "vero": ["vero", "verotus", "tulot"],
    "arviointimenettely": ["arviointimenettely", "kriisikunta", "valvonta", "kriteerit", "tunnusluvut", "raja-arvot"],
    "erityisen vaikea": ["kriisikunta", "arviointimenettely", "taloudellinen asema"],
    "tilinpäätös": ["tilinpäätös", "kirjanpito", "raportointi"],
    "tilintarkast": ["tilintarkastus", "tarkastus", "valvonta"],
    "konsernitilinpäätös": ["konsernitilinpäätös", "kuntakonserni", "raportointi"],
    "toimintakertomus": ["toimintakertomus", "raportointi", "tilinpäätös"],
    "hallintosääntö": ["hallintosääntö", "hallinto", "säännöt"],
    "kunnanjohtaja": ["kunnanjohtaja", "johtaminen", "viranhaltija"],
    "pormestari": ["pormestari", "johtaminen", "luottamushenkilö"],
    "kunnanhallitus": ["kunnanhallitus", "hallinto", "toimielin"],
    "lautakunta": ["lautakunta", "toimielin", "hallinto"],
    "esteellisyys": ["esteellisyys", "jääviys", "päätöksenteko"],
    "oikaisuvaatimus": ["oikaisuvaatimus", "muutoksenhaku", "valitus"],
    "kunnallisvalitus": ["kunnallisvalitus", "muutoksenhaku", "hallinto-oikeus"],
    # COVID-19 / korona synonyms (for 110a)
    "covid": ["korona", "koronaepidemia", "pandemia", "covid-19", "poikkeus", "epidemia"],
    "korona": ["korona", "koronaepidemia", "pandemia", "covid-19", "poikkeus", "epidemia"],
    "epidemia": ["korona", "koronaepidemia", "pandemia", "covid-19", "poikkeus", "epidemia"],
    # Internal control / risk management synonyms (for 115)
    "sisäinen valvonta": ["sisäinen valvonta", "riskienhallinta", "valvonta ja riskit", "kontrollitoiminnot"],
    "sisäisen valvonnan": ["sisäinen valvonta", "riskienhallinta", "valvonta ja riskit", "kontrollitoiminnot"],
    "riskienhallinta": ["riskienhallinta", "sisäinen valvonta", "riskien hallinta", "riskiarviointi"],
    "riskienhallinnan": ["riskienhallinta", "sisäinen valvonta", "riskien hallinta", "riskiarviointi"],
    "olennaiset": ["olennaiset tapahtumat", "merkittävät tapahtumat", "tärkeät tapahtumat"],
    # Crisis municipality synonyms (for 118)
    "tunnusluku": ["tunnusluvut", "raja-arvot", "kriteerit", "kriisikunta"],
    "raja-arvo": ["raja-arvot", "tunnusluvut", "kriteerit", "kriisikunta"],
}

# SOTA: Moment-specific disambiguation tags
# Each moment must have UNIQUE tags to distinguish from siblings
# VERIFIED against actual Kuntalaki 115 § content:
#   115:1 = tavoitteiden toteutuminen, olennaiset asiat
#   115:2 = alijäämäselvitys, talouden tasapainotus (JOS taseessa alijäämää)
#   115:3 = tuloskäsittely (kunnanhallituksen esitys)
MOMENT_SPECIFIC_TAGS: dict[str, dict[str, list[str]]] = {
    # §115 Toimintakertomus - KRIITTINEN: momentit 1, 2, 3 täysin erilaiset
    # VERIFIED from XML:
    #   115:1 = tavoitteet, olennaiset asiat, SISÄINEN VALVONTA, RISKIENHALLINTA
    #   115:2 = alijäämäselvitys (jos taseessa alijäämää)
    #   115:3 = tuloskäsittely
    "115": {
        "1": [
            "tavoitteiden toteutuminen",
            "olennaiset tapahtumat",
            "olennaiset asiat",
            "kuntakonsernin olennaiset asiat",
            "tilikauden jälkeiset tapahtumat",
            "merkittävät tapahtumat",
            "tärkeät tapahtumat",
            "toimintakertomuksen sisältö",
            # Sisäinen valvonta on 115:1:ssä!
            "sisäinen valvonta",
            "sisäisen valvonnan järjestäminen",
            "riskienhallinta",
            "riskienhallinnan järjestäminen",
            "valvonta ja riskit",
            "kontrollit",
        ],
        "2": [
            "alijäämäselvitys",
            "alijäämän kattamissuunnitelma",
            "talouden tasapainotus",
            "tasapainotuksen toteutuminen",
            "taloussuunnitelman riittävyys",
            "kattamaton alijäämä",
            "taseen alijäämä",
        ],
        "3": [
            "tuloksen käsittely",
            "tilikauden tulos",
            "tuloskäsittelyesitys",
            "tuloksen käsittelyesitys",
            "ylijäämän käyttö",
            "alijäämän kattaminen tuloksesta",
        ],
    },
    # §110 vs §110a erottelu
    "110": {
        "default": [
            "talousarvion perussääntö",
            "normaalitilanne",
            "perusmääräaika",
        ],
    },
    "110a": {
        "default": [
            "poikkeus",
            "covid",
            "covid-19",
            "korona",
            "koronaepidemia",
            "pandemia",
            "epidemia",
            "määräajan jatko",
            "poikkeusolosuhteet",
        ],
    },
    # §113 vs §114 erottelu (tilinpäätös vs konsernitilinpäätös)
    "113": {
        "default": [
            "kunnan tilinpäätös",
            "yksittäisen kunnan tilinpäätös",
            "ei konserni",
        ],
    },
    "114": {
        "default": [
            "konsernitilinpäätös",
            "kuntakonsernin tilinpäätös",
            "konsernilaskelmat",
            "konsolidointi",
        ],
    },
    # §118 arviointimenettely momentit
    "118": {
        "1": ["arviointimenettelyn aloittaminen", "valtiovarainministeriö", "menettelyn käynnistäminen"],
        "2": ["alijäämän kattamatta jättäminen", "määräajan ylitys", "arviointimenettelyn edellytykset"],
        "3": ["tunnuslukurajat", "konsernitunnusluvut", "raja-arvot", "kriisikuntakriteerit"],
        "4": ["kuntayhtymän arviointimenettely"],
        "5": ["arviointiryhmä", "ryhmän asettaminen", "jäsenmäärä"],
        "6": ["arviointiryhmän ehdotukset", "valtuuston päätökset", "ehdotusten käsittely"],
        "7": ["menettelyn päättyminen", "seuranta"],
    },
    # §62 vs §62a vs §62b erottelu
    "62": {
        "default": ["kuntayhtymästä eroaminen", "eroaminen", "ei yhdistyminen"],
    },
    "62a": {
        "default": ["kuntayhtymien yhdistyminen", "yhdistyminen", "ei eroaminen"],
    },
    "62b": {
        "default": ["kuntayhtymän jakautuminen", "jakautuminen", "ei eroaminen"],
    },
}


def get_moment_specific_tags(section_id: str, moment: str) -> list[str]:
    """Get moment-specific disambiguation tags for a section/moment combo."""
    tags: list[str] = []
    
    if section_id in MOMENT_SPECIFIC_TAGS:
        section_tags = MOMENT_SPECIFIC_TAGS[section_id]
        # Check for moment-specific tags first
        if moment in section_tags:
            tags.extend(section_tags[moment])
        # Then apply default tags for the section if they exist
        if "default" in section_tags:
            tags.extend(section_tags["default"])
    
    return tags


# v4: MOMENT_ANCHORS - momenttispesifit avaintermit queryn overlap-laskentaan
# Anchors ovat tarkkoja termejä jotka erottavat momentit toisistaan
MOMENT_ANCHORS: dict[str, dict[str, list[str]]] = {
    # §115 Toimintakertomus - kriittiset momenttierot
    "115": {
        "1": [
            "sisäinen valvonta",
            "riskienhallinta",
            "tavoitteiden toteutuminen",
            "tuleva kehitys",
            "olennaiset asiat",
        ],
        "2": [
            "alijäämä",
            "alijäämän kattaminen",
            "kattamistoimenpiteet",
            "talouden tasapainottaminen",
            "tasapainotus",
        ],
        "3": [
            "tuloksen käsittely",
            "tuloskäsittelyesitys",
            "tilikauden tulos",
            "ylijäämän käyttö",
        ],
    },
    # §110 vs §110a
    "110": {
        "default": ["talousarvio", "taloussuunnitelma", "neljä vuotta"],
    },
    "110a": {
        "default": ["covid", "korona", "pandemia", "poikkeus", "epidemia"],
    },
    # §113 vs §114
    "113": {
        "default": ["tilinpäätös", "tilikausi", "kirjanpito"],
    },
    "114": {
        "default": ["konserni", "konsernitilinpäätös", "kuntakonserni", "tytäryhteisö"],
    },
    # §62 vs §62a vs §62b
    "62": {
        "default": ["eroaminen", "kuntayhtymästä eroaminen"],
    },
    "62a": {
        "default": ["yhdistyminen", "kuntayhtymien yhdistyminen"],
    },
    "62b": {
        "default": ["jakautuminen", "kuntayhtymän jakautuminen"],
    },
    # §118 Arviointimenettely
    "118": {
        "1": ["arviointimenettely", "valtiovarainministeriö"],
        "2": ["alijäämän kattamatta jättäminen", "määräajan ylitys"],
        "3": ["tunnuslukurajat", "konsernitunnusluvut", "raja-arvot"],
    },
}


def get_moment_anchors(section_id: str, moment: str) -> list[str]:
    """Get moment-specific anchor terms for query overlap matching."""
    anchors: list[str] = []
    
    if section_id in MOMENT_ANCHORS:
        section_anchors = MOMENT_ANCHORS[section_id]
        # Moment-specific anchors
        if moment in section_anchors:
            anchors.extend(section_anchors[moment])
        # Default anchors for the section
        if "default" in section_anchors:
            anchors.extend(section_anchors["default"])
    
    return anchors


def parse_section_id(raw_section: str) -> tuple[str, int, str | None]:
    """Parse section identifier into components.

    Args:
        raw_section: Raw section string like "110", "110a", "62b"

    Returns:
        Tuple of (section_id, section_num, section_suffix)
        e.g., ("110a", 110, "a") or ("110", 110, None)
    """
    # Remove spaces and §
    section_id = re.sub(r"\s+", "", raw_section)
    section_id = re.sub(r"§", "", section_id).strip()

    # Split into number and suffix
    match = re.match(r"^(\d+)([a-zA-Z]*)$", section_id)
    if match:
        section_num = int(match.group(1))
        section_suffix = match.group(2).lower() if match.group(2) else None
        section_id = f"{section_num}{section_suffix or ''}"
        return section_id, section_num, section_suffix
    else:
        # Fallback for unusual formats
        return section_id, 0, None


@dataclass
class MomentRecord:
    """Single moment/subsection as a JSON record."""

    law: str
    law_id: str
    law_key: str  # SOTA: e.g., "fi:act:410/2015"
    finlex_version: str
    node_id: str  # SOTA: unique identifier for this record
    part: str
    part_title: str
    chapter: str
    chapter_title: str
    section_id: str  # SOTA: e.g., "110a"
    section_num: int  # SOTA: e.g., 110
    section_suffix: str | None  # SOTA: e.g., "a" or None
    section_title: str
    moment: str
    text: str
    effective_from: str
    in_force: bool
    tags: list[str] = field(default_factory=list)
    anchors: list[str] = field(default_factory=list)  # v4: moment-specific anchor terms
    source: dict[str, str] = field(default_factory=dict)


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def extract_text(node: etree._Element) -> str:
    """Extract all text content from a node."""
    text = " ".join(" ".join(node.itertext()).split())
    return normalize_whitespace(text)


def first_element(node: etree._Element, local_name: str) -> Optional[etree._Element]:
    """Get first child element by local name."""
    result = node.xpath(f"./*[local-name()='{local_name}'][1]")
    return result[0] if result else None


def first_text(node: etree._Element, local_name: str) -> str:
    """Get text content of first child element by local name."""
    el = first_element(node, local_name)
    return extract_text(el) if el is not None else ""


def derive_tags(
    part_title: str,
    chapter_title: str,
    section_title: str,
    text: str,
) -> list[str]:
    """Derive semantic tags from context and content."""
    tags: set[str] = set()
    combined = f"{part_title} {chapter_title} {section_title} {text}".lower()

    # Check chapter-based tags
    for keyword, tag_list in CHAPTER_TAGS.items():
        if keyword in combined:
            tags.update(tag_list)

    # Check keyword-based tags
    for keyword, tag_list in KEYWORD_TAGS.items():
        if keyword in combined:
            tags.update(tag_list)

    # Add section-specific tag from title
    if section_title:
        # Extract key concept from section title
        title_lower = section_title.lower()
        if "§" in section_title:
            title_lower = section_title.split("§", 1)[-1].strip().lower()
        if title_lower:
            tags.add(title_lower)

    return sorted(tags)


def extract_subsection_text(subsection: etree._Element) -> str:
    """Extract text from a subsection, handling intro, content, and paragraphs."""
    parts: list[str] = []

    # Get intro text
    intro = first_element(subsection, "intro")
    if intro is not None:
        intro_text = extract_text(intro)
        if intro_text:
            parts.append(intro_text)

    # Get content text
    content = first_element(subsection, "content")
    if content is not None:
        content_text = extract_text(content)
        if content_text:
            parts.append(content_text)

    # Get paragraph texts (numbered items)
    paragraphs = subsection.xpath("./*[local-name()='paragraph']")
    for para in paragraphs:
        num = first_text(para, "num")
        para_content = first_element(para, "content")
        para_text = extract_text(para_content) if para_content is not None else ""
        if para_text:
            if num:
                parts.append(f"{num} {para_text}")
            else:
                parts.append(para_text)

    return " ".join(parts)


def parse_kuntalaki_xml(xml_path: Path) -> list[MomentRecord]:
    """Parse Kuntalaki AKN XML and extract all moments as records."""
    tree = etree.parse(str(xml_path))
    root = tree.getroot()

    records: list[MomentRecord] = []
    seen_node_ids: set[str] = set()  # For duplicate validation

    # Extract metadata
    law_id = "410/2015"
    law_name = "Kuntalaki"
    law_key = "fi:act:410/2015"  # SOTA: canonical law key

    # Get version from FRBRversionNumber
    version_el = root.xpath("//*[local-name()='FRBRversionNumber']/@value")
    finlex_version = f"fin@{version_el[0]}" if version_el else ""

    # Get effective date
    effective_el = root.xpath("//*[local-name()='dateEntryIntoForce']/@date")
    effective_from = effective_el[0] if effective_el else "2015-05-01"

    # Check if in force
    in_force_el = root.xpath("//*[local-name()='isInForce']/@value")
    in_force = in_force_el[0].lower() == "true" if in_force_el else True

    # Build source metadata
    rel_xml_path = str(xml_path).replace("\\", "/")
    if "finlex_statute_consolidated" in rel_xml_path:
        rel_xml_path = "finlex_statute_consolidated" + rel_xml_path.split(
            "finlex_statute_consolidated"
        )[-1]

    finlex_url = f"https://finlex.fi/fi/laki/ajantasa/2015/20150410"

    # Navigate body structure
    body = root.xpath("//*[local-name()='body'][1]")
    if not body:
        raise ValueError("BODY element not found in XML")
    body = body[0]

    # Process parts
    parts = body.xpath(".//*[local-name()='part']")
    for part in parts:
        part_num = first_text(part, "num")
        part_heading = first_text(part, "heading")

        # Process chapters within part
        chapters = part.xpath("./*[local-name()='chapter']")
        for chapter in chapters:
            chapter_num = first_text(chapter, "num")
            chapter_heading = first_text(chapter, "heading")

            # Process sections within chapter
            sections = chapter.xpath("./*[local-name()='section']")
            for section in sections:
                section_num_raw = first_text(section, "num")
                section_heading = first_text(section, "heading")

                # SOTA: Parse section identifier into components
                sec_id, sec_num, sec_suffix = parse_section_id(section_num_raw)

                # Process subsections (moments) within section
                subsections = section.xpath("./*[local-name()='subsection']")

                if not subsections:
                    # Section without subsections - treat as single moment
                    text = extract_text(section)
                    # Remove num and heading from text
                    for remove_part in [section_num_raw, section_heading]:
                        if remove_part:
                            text = text.replace(remove_part, "", 1).strip()

                    if text:
                        moment_num = "1"
                        # SOTA: Build unique node_id
                        node_id = f"{law_id}:{finlex_version}:{sec_id}:{moment_num}"

                        # Validate uniqueness
                        if node_id in seen_node_ids:
                            raise ValueError(f"Duplicate node_id detected: {node_id}")
                        seen_node_ids.add(node_id)

                        tags = derive_tags(
                            part_heading, chapter_heading, section_heading, text
                        )
                        # SOTA: Add moment-specific disambiguation tags
                        moment_tags = get_moment_specific_tags(sec_id, moment_num)
                        tags = sorted(set(tags) | set(moment_tags))
                        # v4: Get moment-specific anchors
                        anchors = get_moment_anchors(sec_id, moment_num)
                        
                        record = MomentRecord(
                            law=law_name,
                            law_id=law_id,
                            law_key=law_key,
                            finlex_version=finlex_version,
                            node_id=node_id,
                            part=part_num,
                            part_title=part_heading,
                            chapter=chapter_num,
                            chapter_title=chapter_heading,
                            section_id=sec_id,
                            section_num=sec_num,
                            section_suffix=sec_suffix,
                            section_title=section_heading,
                            moment=moment_num,
                            text=text,
                            effective_from=effective_from,
                            in_force=in_force,
                            tags=tags,
                            anchors=anchors,
                            source={
                                "xml_path": rel_xml_path,
                                "finlex_url": finlex_url,
                                "xpath": f"//section[@eId='{section.get('eId', '')}']",
                            },
                        )
                        records.append(record)
                else:
                    # Process each subsection as separate moment
                    for i, subsection in enumerate(subsections, 1):
                        text = extract_subsection_text(subsection)

                        if text:
                            moment_num = str(i)
                            # SOTA: Build unique node_id
                            node_id = f"{law_id}:{finlex_version}:{sec_id}:{moment_num}"

                            # Validate uniqueness
                            if node_id in seen_node_ids:
                                raise ValueError(f"Duplicate node_id detected: {node_id}")
                            seen_node_ids.add(node_id)

                            tags = derive_tags(
                                part_heading, chapter_heading, section_heading, text
                            )
                            # SOTA: Add moment-specific disambiguation tags
                            moment_tags = get_moment_specific_tags(sec_id, moment_num)
                            tags = sorted(set(tags) | set(moment_tags))
                            # v4: Get moment-specific anchors
                            anchors = get_moment_anchors(sec_id, moment_num)
                            
                            record = MomentRecord(
                                law=law_name,
                                law_id=law_id,
                                law_key=law_key,
                                finlex_version=finlex_version,
                                node_id=node_id,
                                part=part_num,
                                part_title=part_heading,
                                chapter=chapter_num,
                                chapter_title=chapter_heading,
                                section_id=sec_id,
                                section_num=sec_num,
                                section_suffix=sec_suffix,
                                section_title=section_heading,
                                moment=moment_num,
                                text=text,
                                effective_from=effective_from,
                                in_force=in_force,
                                tags=tags,
                                anchors=anchors,
                                source={
                                    "xml_path": rel_xml_path,
                                    "finlex_url": finlex_url,
                                    "xpath": f"//subsection[@eId='{subsection.get('eId', '')}']",
                                },
                            )
                            records.append(record)

    return records


def write_json_records(records: list[MomentRecord], output_path: Path) -> None:
    """Write records to JSON file."""
    data = [asdict(r) for r in records]
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Wrote {len(records)} records to {output_path}")


def write_jsonl_records(records: list[MomentRecord], output_path: Path) -> None:
    """Write records to JSONL file (one record per line, better for streaming)."""
    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
    print(f"Wrote {len(records)} records to {output_path}")


def main() -> None:
    """Main entry point."""
    # Find Kuntalaki XML (latest version)
    base_path = Path(__file__).parent.parent
    kuntalaki_dir = (
        base_path
        / "finlex_statute_consolidated"
        / "akn"
        / "fi"
        / "act"
        / "statute-consolidated"
        / "2015"
        / "410"
    )

    if not kuntalaki_dir.exists():
        print(f"ERROR: Kuntalaki directory not found: {kuntalaki_dir}")
        sys.exit(1)

    # Find latest version (highest fin@ number)
    # Filter out "fin@" without version number and Swedish versions
    fin_dirs = [
        d
        for d in kuntalaki_dir.iterdir()
        if d.is_dir()
        and d.name.startswith("fin@")
        and len(d.name) > 4  # Must have version number after "fin@"
    ]
    versions = sorted(
        fin_dirs,
        key=lambda d: int(d.name.replace("fin@", "")),
        reverse=True,
    )

    if not versions:
        print(f"ERROR: No fin@ versions found in {kuntalaki_dir}")
        sys.exit(1)

    latest_version = versions[0]
    xml_path = latest_version / "main.xml"

    if not xml_path.exists():
        print(f"ERROR: main.xml not found: {xml_path}")
        sys.exit(1)

    print(f"Processing: {xml_path}")
    print(f"Version: {latest_version.name}")

    # Parse and extract records
    records = parse_kuntalaki_xml(xml_path)

    # Write outputs
    output_dir = base_path / "analysis_layer" / "json"
    output_dir.mkdir(parents=True, exist_ok=True)

    # JSON array format
    json_output = output_dir / "kuntalaki_410-2015.json"
    write_json_records(records, json_output)

    # JSONL format (one record per line)
    jsonl_output = output_dir / "kuntalaki_410-2015.jsonl"
    write_jsonl_records(records, jsonl_output)

    # Print summary statistics
    print("\n--- Summary ---")
    print(f"Total moments: {len(records)}")

    sections = set(r.section_id for r in records)
    print(f"Unique sections: {len(sections)}")

    all_tags = set()
    for r in records:
        all_tags.update(r.tags)
    print(f"Unique tags: {len(all_tags)}")
    print(f"Tags: {', '.join(sorted(all_tags)[:20])}...")


if __name__ == "__main__":
    main()

