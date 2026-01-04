"""
Kuntalaki versiohistoria (lineage) -generaattori.

Kerää kaikki fin@-versiot ja muodostaa aikajanan.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from lxml import etree


@dataclass
class VersionInfo:
    """Version information for a law."""

    finlex: str  # SOTA: renamed from finlex_version
    effective_from: str
    source_xml: str  # SOTA: path to source XML
    date_consolidated: str
    amendments: list[str]


def extract_version_info(xml_path: Path) -> VersionInfo | None:
    """Extract version info from a Kuntalaki XML file."""
    try:
        tree = etree.parse(str(xml_path))
        root = tree.getroot()

        # Get version
        version_el = root.xpath("//*[local-name()='FRBRversionNumber']/@value")
        version = version_el[0] if version_el else ""

        # Get effective date
        effective_el = root.xpath(
            "//*[local-name()='finlex:inForce']/*[local-name()='finlex:dateEntryIntoForce']/@date"
        )
        if not effective_el:
            effective_el = root.xpath(
                "//*[local-name()='dateEntryIntoForce']/@date"
            )
        effective_from = effective_el[0] if effective_el else ""

        # Get consolidated date
        consolidated_el = root.xpath(
            "//*[local-name()='FRBRdate'][@name='dateConsolidated']/@date"
        )
        date_consolidated = consolidated_el[0] if consolidated_el else ""

        # Get amendments
        amendments: list[str] = []
        amendment_refs = root.xpath(
            "//*[local-name()='amendedBy']/*[local-name()='statuteReference']"
        )
        for ref in amendment_refs:
            ref_el = ref.xpath("./*[local-name()='ref']/@href")
            note_el = ref.xpath("./*[local-name()='noteEditorial']/text()")
            if ref_el:
                amendment_id = ref_el[0].split("/")[-1]
                note = note_el[0] if note_el else ""
                amendments.append(f"{amendment_id}: {note}" if note else amendment_id)

        # Build relative source path
        rel_xml_path = str(xml_path).replace("\\", "/")
        if "finlex_statute_consolidated" in rel_xml_path:
            rel_xml_path = "finlex_statute_consolidated" + rel_xml_path.split(
                "finlex_statute_consolidated"
            )[-1]

        return VersionInfo(
            finlex=f"fin@{version}",
            effective_from=effective_from,
            source_xml=rel_xml_path,
            date_consolidated=date_consolidated,
            amendments=amendments,
        )

    except Exception as e:
        print(f"Warning: Could not parse {xml_path}: {e}")
        return None


def main() -> None:
    """Main entry point."""
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

    # Find all Finnish versions
    fin_dirs = sorted(
        [
            d
            for d in kuntalaki_dir.iterdir()
            if d.is_dir() and d.name.startswith("fin@") and len(d.name) > 4
        ],
        key=lambda d: int(d.name.replace("fin@", "")),
    )

    print(f"Found {len(fin_dirs)} versions")

    versions: list[dict] = []
    for version_dir in fin_dirs:
        xml_path = version_dir / "main.xml"
        if xml_path.exists():
            info = extract_version_info(xml_path)
            if info:
                versions.append(asdict(info))
                print(f"  {info.finlex}: {info.effective_from}")

    # Build lineage structure
    lineage = {
        "law": "Kuntalaki",
        "law_id": "410/2015",
        "versions": versions,
        "version_count": len(versions),
        "latest_version": versions[-1]["finlex"] if versions else None,
    }

    # Write output
    output_dir = base_path / "analysis_layer" / "lineage"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "kuntalaki_410-2015_versions.json"
    output_path.write_text(
        json.dumps(lineage, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\nWrote lineage to {output_path}")


if __name__ == "__main__":
    main()

