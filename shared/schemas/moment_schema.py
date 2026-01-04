"""
Shared schema for law moments across all laws.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MomentRecord:
    """Standard schema for a single moment (subsection) in any Finnish law."""
    
    # Law identification
    law: str                          # Human-readable law name (e.g., "Kuntalaki")
    law_id: str                       # Finlex ID (e.g., "410/2015")
    law_key: str                      # Internal key (e.g., "fi:act:410/2015")
    node_id: str                      # Unique ID (e.g., "410/2015:fin@20230780:110a:3")
    finlex_version: str               # Finlex version (e.g., "fin@20230780")
    
    # Structure
    part: str                         # Part name (e.g., "VI OSA")
    part_title: str                   # Part title
    chapter: str                      # Chapter (e.g., "13 luku")
    chapter_title: str                # Chapter title
    section_id: str                   # Section ID with suffix (e.g., "110a")
    section_num: int                  # Section number only (e.g., 110)
    section_suffix: Optional[str]     # Section suffix or None (e.g., "a")
    section_title: str                # Section title
    moment: int                       # Moment number (1, 2, 3...)
    
    # Content
    text: str                         # Full text of the moment
    
    # Metadata
    effective_from: str               # ISO date
    in_force: bool                    # Is currently in force
    tags: list[str] = field(default_factory=list)     # Semantic tags
    anchors: list[str] = field(default_factory=list)  # Moment-specific keywords
    
    # Source
    source: dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "law": self.law,
            "law_id": self.law_id,
            "law_key": self.law_key,
            "node_id": self.node_id,
            "finlex_version": self.finlex_version,
            "part": self.part,
            "part_title": self.part_title,
            "chapter": self.chapter,
            "chapter_title": self.chapter_title,
            "section_id": self.section_id,
            "section_num": self.section_num,
            "section_suffix": self.section_suffix,
            "section_title": self.section_title,
            "moment": self.moment,
            "text": self.text,
            "effective_from": self.effective_from,
            "in_force": self.in_force,
            "tags": self.tags,
            "anchors": self.anchors,
            "source": self.source,
        }

