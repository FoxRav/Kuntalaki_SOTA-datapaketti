"""
Generic law builder for processing any Finlex AKN XML into normalized JSON/JSONL.

This is the shared infrastructure for processing multiple Finnish laws.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Any

from lxml import etree


@dataclass
class LawConfig:
    """Configuration for a specific law."""
    law_key: str              # e.g., "kuntalaki_410_2015"
    law_id: str               # e.g., "410/2015"
    law_name: str             # e.g., "Kuntalaki"
    law_key_canonical: str    # e.g., "fi:act:410/2015"
    finlex_url_base: str      # e.g., "https://finlex.fi/fi/laki/ajantasa/2015/20150410"
    xml_base_path: Path       # e.g., Path("finlex_statute.../2015/410")
    
    # Optional: Law-specific keyword tags
    keyword_tags: dict[str, list[str]] = field(default_factory=dict)
    chapter_tags: dict[str, list[str]] = field(default_factory=dict)
    moment_specific_tags: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    moment_anchors: dict[str, dict[str, list[str]]] = field(default_factory=dict)


@dataclass
class MomentRecord:
    """Single moment/subsection as a JSON record."""

    law: str
    law_id: str
    law_key: str
    finlex_version: str
    node_id: str
    part: str
    part_title: str
    chapter: str
    chapter_title: str
    section_id: str
    section_num: int
    section_suffix: str | None
    section_title: str
    moment: str
    text: str
    effective_from: str
    in_force: bool
    tags: list[str] = field(default_factory=list)
    anchors: list[str] = field(default_factory=list)
    source: dict[str, str] = field(default_factory=dict)


# Default chapter-based tags (shared across laws)
DEFAULT_CHAPTER_TAGS: dict[str, list[str]] = {
    "talous": ["talous", "budjetti", "rahoitus"],
    "kirjanpito": ["kirjanpito", "tilinpäätös", "laskentatoimi"],
    "tarkastus": ["tarkastus", "tilintarkastus", "valvonta"],
    "hallinto": ["hallinto", "organisaatio", "johtaminen"],
    "tase": ["tase", "vastaavaa", "vastattavaa", "tilinpäätös"],
    "tuloslaskelma": ["tuloslaskelma", "tuotot", "kulut", "tilinpäätös"],
    "liitetiedot": ["liitetiedot", "liitteet", "tilinpäätös"],
    "toimintakertomus": ["toimintakertomus", "raportointi", "tilinpäätös"],
    "arvostus": ["arvostus", "hankintameno", "käypä arvo"],
    "poisto": ["poisto", "hankintameno", "vaikutusaika"],
}

# Default keyword-based tags
DEFAULT_KEYWORD_TAGS: dict[str, list[str]] = {
    "tilinpäätös": ["tilinpäätös", "kirjanpito", "raportointi"],
    "tilikausi": ["tilikausi", "tilivuosi", "vuosijakso"],
    "kirjanpitovelvollinen": ["kirjanpitovelvollinen", "velvollisuus"],
    "tase": ["tase", "vastaavaa", "vastattavaa"],
    "tuloslaskelma": ["tuloslaskelma", "tulos", "tilinpäätös"],
    "toimintakertomus": ["toimintakertomus", "raportointi"],
    "tilintarkast": ["tilintarkastus", "tarkastus", "valvonta"],
}


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


def parse_section_id(raw_section: str) -> tuple[str, int, str | None]:
    """Parse section identifier into components."""
    section_id = re.sub(r"\s+", "", raw_section)
    section_id = re.sub(r"§", "", section_id).strip()

    match = re.match(r"^(\d+)([a-zA-Z]*)$", section_id)
    if match:
        section_num = int(match.group(1))
        section_suffix = match.group(2).lower() if match.group(2) else None
        section_id = f"{section_num}{section_suffix or ''}"
        return section_id, section_num, section_suffix
    else:
        return section_id, 0, None


def derive_tags(
    config: LawConfig,
    part_title: str,
    chapter_title: str,
    section_title: str,
    text: str,
    section_id: str,
    moment: str,
) -> tuple[list[str], list[str]]:
    """
    Derive semantic tags and anchors from context and content.
    
    Returns:
        Tuple of (tags, anchors)
    """
    tags: set[str] = set()
    combined = f"{part_title} {chapter_title} {section_title} {text}".lower()

    # Check chapter-based tags (default + law-specific)
    all_chapter_tags = {**DEFAULT_CHAPTER_TAGS, **config.chapter_tags}
    for keyword, tag_list in all_chapter_tags.items():
        if keyword in combined:
            tags.update(tag_list)

    # Check keyword-based tags (default + law-specific)
    all_keyword_tags = {**DEFAULT_KEYWORD_TAGS, **config.keyword_tags}
    for keyword, tag_list in all_keyword_tags.items():
        if keyword in combined:
            tags.update(tag_list)

    # Add section-specific tag from title
    if section_title:
        title_lower = section_title.lower()
        if "§" in section_title:
            title_lower = section_title.split("§", 1)[-1].strip().lower()
        if title_lower:
            tags.add(title_lower)

    # Check moment-specific tags
    if section_id in config.moment_specific_tags:
        section_tags = config.moment_specific_tags[section_id]
        if moment in section_tags:
            tags.update(section_tags[moment])
        if "default" in section_tags:
            tags.update(section_tags["default"])

    # Get anchors
    anchors: list[str] = []
    if section_id in config.moment_anchors:
        section_anchors = config.moment_anchors[section_id]
        if moment in section_anchors:
            anchors.extend(section_anchors[moment])
        if "default" in section_anchors:
            anchors.extend(section_anchors["default"])

    return sorted(tags), anchors


def extract_subsection_text(subsection: etree._Element) -> str:
    """Extract text from a subsection, handling intro, content, and paragraphs."""
    parts: list[str] = []

    intro = first_element(subsection, "intro")
    if intro is not None:
        intro_text = extract_text(intro)
        if intro_text:
            parts.append(intro_text)

    content = first_element(subsection, "content")
    if content is not None:
        content_text = extract_text(content)
        if content_text:
            parts.append(content_text)

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


def find_latest_xml(base_path: Path, lang_prefix: str = "fin@") -> Path:
    """Find the latest version XML file."""
    # Find version directories
    version_dirs = [
        d for d in base_path.iterdir()
        if d.is_dir() and d.name.startswith(lang_prefix) and len(d.name) > len(lang_prefix)
    ]
    
    if not version_dirs:
        raise ValueError(f"No {lang_prefix} versions found in {base_path}")
    
    # Sort by version number (assuming numeric after prefix)
    def get_version_num(d: Path) -> int:
        try:
            return int(d.name.replace(lang_prefix, ""))
        except ValueError:
            return 0
    
    versions = sorted(version_dirs, key=get_version_num, reverse=True)
    latest = versions[0]
    
    xml_path = latest / "main.xml"
    if not xml_path.exists():
        raise ValueError(f"main.xml not found: {xml_path}")
    
    return xml_path


def parse_law_xml(config: LawConfig, xml_path: Path) -> list[MomentRecord]:
    """Parse AKN XML and extract all moments as records."""
    tree = etree.parse(str(xml_path))
    root = tree.getroot()

    records: list[MomentRecord] = []
    seen_node_ids: set[str] = set()

    # Get version from FRBRversionNumber
    version_el = root.xpath("//*[local-name()='FRBRversionNumber']/@value")
    finlex_version = f"fin@{version_el[0]}" if version_el else ""

    # Get effective date
    effective_el = root.xpath("//*[local-name()='dateEntryIntoForce']/@date")
    effective_from = effective_el[0] if effective_el else "1900-01-01"

    # Check if in force
    in_force_el = root.xpath("//*[local-name()='isInForce']/@value")
    in_force = in_force_el[0].lower() == "true" if in_force_el else True

    # Build source metadata
    rel_xml_path = str(xml_path).replace("\\", "/")
    if "finlex_statute_consolidated" in rel_xml_path:
        rel_xml_path = "finlex_statute_consolidated" + rel_xml_path.split(
            "finlex_statute_consolidated"
        )[-1]

    # Navigate body structure
    body = root.xpath("//*[local-name()='body'][1]")
    if not body:
        raise ValueError("BODY element not found in XML")
    body = body[0]

    # Try different structure patterns
    # Pattern 1: part > chapter > section (Kuntalaki style)
    # Pattern 2: hcontainer > chapter > section (Kirjanpitolaki style)
    # Pattern 3: chapter > section (simpler laws)
    # Pattern 4: Direct sections (very simple laws)
    
    parts = body.xpath(".//*[local-name()='part']")
    if parts:
        for part in parts:
            part_num = first_text(part, "num")
            part_heading = first_text(part, "heading")
            
            chapters = part.xpath("./*[local-name()='chapter']")
            for chapter in chapters:
                _process_chapter(
                    config, chapter, part_num, part_heading, 
                    finlex_version, effective_from, in_force,
                    rel_xml_path, records, seen_node_ids
                )
    else:
        # Try hcontainer > chapter pattern (Kirjanpitolaki style)
        hcontainers = body.xpath("./*[local-name()='hcontainer']")
        processed_via_hcontainer = False
        
        if hcontainers:
            for hcontainer in hcontainers:
                hc_num = first_text(hcontainer, "num")
                hc_heading = first_text(hcontainer, "heading")
                
                chapters = hcontainer.xpath("./*[local-name()='chapter']")
                for chapter in chapters:
                    _process_chapter(
                        config, chapter, hc_num, hc_heading,
                        finlex_version, effective_from, in_force,
                        rel_xml_path, records, seen_node_ids
                    )
                    processed_via_hcontainer = True
                
                # Also check for sections directly under hcontainer
                sections = hcontainer.xpath("./*[local-name()='section']")
                for section in sections:
                    _process_section(
                        config, section, hc_num, hc_heading, "", "",
                        finlex_version, effective_from, in_force,
                        rel_xml_path, records, seen_node_ids
                    )
                    processed_via_hcontainer = True
        
        # Only try other patterns if we didn't process via hcontainer
        if not processed_via_hcontainer:
            # Try chapters directly under body
            chapters = body.xpath("./*[local-name()='chapter']")
            if chapters:
                for chapter in chapters:
                    _process_chapter(
                        config, chapter, "", "",
                        finlex_version, effective_from, in_force,
                        rel_xml_path, records, seen_node_ids
                    )
            else:
                # Try sections directly under body
                sections = body.xpath("./*[local-name()='section']")
                for section in sections:
                    _process_section(
                        config, section, "", "", "", "",
                        finlex_version, effective_from, in_force,
                        rel_xml_path, records, seen_node_ids
                    )

    return records


def _process_chapter(
    config: LawConfig,
    chapter: etree._Element,
    part_num: str,
    part_heading: str,
    finlex_version: str,
    effective_from: str,
    in_force: bool,
    rel_xml_path: str,
    records: list[MomentRecord],
    seen_node_ids: set[str],
) -> None:
    """Process a chapter element."""
    chapter_num = first_text(chapter, "num")
    chapter_heading = first_text(chapter, "heading")

    sections = chapter.xpath("./*[local-name()='section']")
    for section in sections:
        _process_section(
            config, section, part_num, part_heading,
            chapter_num, chapter_heading,
            finlex_version, effective_from, in_force,
            rel_xml_path, records, seen_node_ids
        )


def _process_section(
    config: LawConfig,
    section: etree._Element,
    part_num: str,
    part_heading: str,
    chapter_num: str,
    chapter_heading: str,
    finlex_version: str,
    effective_from: str,
    in_force: bool,
    rel_xml_path: str,
    records: list[MomentRecord],
    seen_node_ids: set[str],
) -> None:
    """Process a section element."""
    section_num_raw = first_text(section, "num")
    section_heading = first_text(section, "heading")

    sec_id, sec_num, sec_suffix = parse_section_id(section_num_raw)

    subsections = section.xpath("./*[local-name()='subsection']")

    if not subsections:
        # Section without subsections - treat as single moment
        text = extract_text(section)
        for remove_part in [section_num_raw, section_heading]:
            if remove_part:
                text = text.replace(remove_part, "", 1).strip()

        if text:
            _add_record(
                config, "1", text, sec_id, sec_num, sec_suffix, section_heading,
                part_num, part_heading, chapter_num, chapter_heading,
                finlex_version, effective_from, in_force, rel_xml_path,
                section.get('eId', ''), records, seen_node_ids
            )
    else:
        for i, subsection in enumerate(subsections, 1):
            text = extract_subsection_text(subsection)
            if text:
                _add_record(
                    config, str(i), text, sec_id, sec_num, sec_suffix, section_heading,
                    part_num, part_heading, chapter_num, chapter_heading,
                    finlex_version, effective_from, in_force, rel_xml_path,
                    subsection.get('eId', ''), records, seen_node_ids
                )


def _add_record(
    config: LawConfig,
    moment_num: str,
    text: str,
    sec_id: str,
    sec_num: int,
    sec_suffix: str | None,
    section_heading: str,
    part_num: str,
    part_heading: str,
    chapter_num: str,
    chapter_heading: str,
    finlex_version: str,
    effective_from: str,
    in_force: bool,
    rel_xml_path: str,
    xpath_id: str,
    records: list[MomentRecord],
    seen_node_ids: set[str],
) -> None:
    """Add a single moment record."""
    # Build unique node_id including chapter if sections repeat across chapters
    # Extract chapter identifier (e.g., "1 luku" -> "1", "7 a luku" -> "7a", "3 a luku" -> "3a")
    ch_id = ""
    if chapter_num:
        # Match patterns like "1 luku", "7 a luku", "3 a luku"
        ch_match = re.match(r"(\d+)\s*([a-z]?)", chapter_num.strip().lower())
        if ch_match:
            ch_id = ch_match.group(1) + (ch_match.group(2) or "")
    
    # Include chapter in node_id if we have one
    if ch_id:
        node_id = f"{config.law_id}:{finlex_version}:{ch_id}:{sec_id}:{moment_num}"
    else:
        node_id = f"{config.law_id}:{finlex_version}:{sec_id}:{moment_num}"

    if node_id in seen_node_ids:
        raise ValueError(f"Duplicate node_id detected: {node_id}")
    seen_node_ids.add(node_id)

    tags, anchors = derive_tags(
        config, part_heading, chapter_heading, section_heading, text,
        sec_id, moment_num
    )

    record = MomentRecord(
        law=config.law_name,
        law_id=config.law_id,
        law_key=config.law_key_canonical,
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
            "finlex_url": config.finlex_url_base,
            "xpath": f"//*[@eId='{xpath_id}']",
        },
    )
    records.append(record)


def write_json_records(records: list[MomentRecord], output_path: Path) -> None:
    """Write records to JSON file."""
    data = [asdict(r) for r in records]
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Wrote {len(records)} records to {output_path}")


def write_jsonl_records(records: list[MomentRecord], output_path: Path) -> None:
    """Write records to JSONL file."""
    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
    print(f"Wrote {len(records)} records to {output_path}")


def build_law(config: LawConfig, output_dir: Path) -> list[MomentRecord]:
    """Build JSON/JSONL for a law based on config."""
    print(f"Processing: {config.law_name} ({config.law_id})")
    
    # Find latest XML
    xml_path = find_latest_xml(config.xml_base_path)
    print(f"  XML: {xml_path}")
    print(f"  Version: {xml_path.parent.name}")
    
    # Parse and extract records
    records = parse_law_xml(config, xml_path)
    
    # Write outputs
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create filename from law_key
    filename_base = config.law_key.replace("_", "-")
    
    json_output = output_dir / f"{filename_base}.json"
    write_json_records(records, json_output)
    
    jsonl_output = output_dir / f"{filename_base}.jsonl"
    write_jsonl_records(records, jsonl_output)
    
    # Print summary
    print(f"\n--- {config.law_name} Summary ---")
    print(f"  Total moments: {len(records)}")
    print(f"  Unique sections: {len(set(r.section_id for r in records))}")
    
    all_tags = set()
    for r in records:
        all_tags.update(r.tags)
    print(f"  Unique tags: {len(all_tags)}")
    
    return records

