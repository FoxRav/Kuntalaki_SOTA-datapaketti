"""
Kuntalaki JSON → LLM-optimoitu Markdown -muunnos.

Tuottaa pykälä-/momentti-tasolla jäsennellyn Markdownin.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def build_markdown(records: list[dict[str, Any]]) -> str:
    """Build Markdown document from JSON records."""
    lines: list[str] = []

    lines.append("# Kuntalaki 410/2015")
    lines.append("")
    lines.append("_Ajantasainen säädös, lähde: Finlex_")
    lines.append("")
    lines.append("---")
    lines.append("")

    current_part = ""
    current_chapter = ""
    current_section = ""

    for record in records:
        # Part header
        part_key = f"{record['part']} {record['part_title']}"
        if part_key != current_part:
            current_part = part_key
            lines.append(f"## {record['part']} {record['part_title']}")
            lines.append("")

        # Chapter header
        chapter_key = f"{record['chapter']} {record['chapter_title']}"
        if chapter_key != current_chapter:
            current_chapter = chapter_key
            lines.append(f"### {record['chapter']} {record['chapter_title']}")
            lines.append("")

        # Section header (only once per section)
        section_key = f"{record['section']} {record['section_title']}"
        if section_key != current_section:
            current_section = section_key
            lines.append(f"#### § {record['section']} {record['section_title']}")
            lines.append("")

        # Moment text
        moment = record["moment"]
        text = record["text"]

        if moment == "1" and len([r for r in records if r["section"] == record["section"]]) == 1:
            # Single moment section - no numbering needed
            lines.append(text)
        else:
            lines.append(f"**{record['section']}.{moment} mom.** {text}")

        lines.append("")

    # Add footer with source info
    lines.append("---")
    lines.append("")
    lines.append("_Lähde: Kuntalaki 410/2015, Finlex, voimassa._")
    lines.append(f"_Versio: {records[0]['finlex_version'] if records else 'N/A'}_")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    """Main entry point."""
    base_path = Path(__file__).parent.parent
    json_path = base_path / "analysis_layer" / "json" / "kuntalaki_410-2015.json"

    if not json_path.exists():
        print(f"ERROR: JSON file not found: {json_path}")
        print("Run build_kuntalaki_json.py first.")
        sys.exit(1)

    # Load records
    records = json.loads(json_path.read_text(encoding="utf-8"))
    print(f"Loaded {len(records)} records from {json_path}")

    # Build Markdown
    md_content = build_markdown(records)

    # Write output
    output_dir = base_path / "analysis_layer" / "markdown"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "kuntalaki_410-2015.md"
    output_path.write_text(md_content, encoding="utf-8")

    print(f"Wrote Markdown to {output_path}")
    print(f"Size: {len(md_content):,} characters")


if __name__ == "__main__":
    main()

