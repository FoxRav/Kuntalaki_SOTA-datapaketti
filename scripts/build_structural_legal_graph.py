#!/usr/bin/env python3
"""
v8: Build Structural Legal Graph

Builds nodes.jsonl and edges.jsonl from law JSONL files.
Parses references (REFERS_TO) and exceptions (EXCEPTS) from legal text.

Usage:
    python scripts/build_structural_legal_graph.py
"""

import json
import re
import sys
from pathlib import Path
from typing import TypedDict

PROJECT_ROOT = Path(__file__).parent.parent


class Node(TypedDict):
    """Node in the legal graph."""
    node_id: str
    node_type: str  # LAW, SECTION, MOMENT
    law_key: str
    section_num: int | None
    moment: int | str | None
    section_title: str
    text: str


class Edge(TypedDict):
    """Edge in the legal graph."""
    source: str  # node_id
    target: str  # node_id (or partial reference)
    edge_type: str  # REFERS_TO, EXCEPTS, HAS_SECTION, HAS_MOMENT, DEFINES
    context: str  # The text snippet containing the reference


# v8.1: Improved regex patterns for parsing references with Finnish declensions
# Handles: §, §:n, §:ssä, §:ssa, §:ään, §:stä, etc.

# Pattern: "X §:n Y momentissa/momentti/mom." 
SECTION_MOMENT_PATTERN = re.compile(
    r"(\d+)\s*§:?(?:n|ssä|ssa|ään|stä|sta|lta|lle|lla)?\s+(\d+)\s*(?:momentti|mom\.?|momentissa|momentti(?:in|a|ssa))",
    re.IGNORECASE
)

# Pattern: "X §:ssä" or "X §:n" with declension
SECTION_DECL_PATTERN = re.compile(
    r"(\d+)\s*§:?(?:n|ssä|ssa|ään|stä|sta|lta|lle|lla)",
    re.IGNORECASE
)

# Pattern: simple "X §" reference (basic)
SIMPLE_SECTION_PATTERN = re.compile(r"(\d+)\s*§")

# Pattern: "N luvun M §" or "N luku M §"
CHAPTER_SECTION_PATTERN = re.compile(
    r"(\d+)\s*(?:luvun|luku)\s+(\d+)\s*§",
    re.IGNORECASE
)

# Pattern for external law references: "lain (XXXX/YYYY) X luvun Y §"
EXTERNAL_LAW_PATTERN = re.compile(
    r"(\w+lain?|asetuksen?)\s*\((\d+/\d+)\)",
    re.IGNORECASE
)

# v8.1: Known law names to IDs mapping (for references without explicit ID)
KNOWN_LAWS = {
    "kirjanpitolaki": "1336/1997",
    "kirjanpitolakia": "1336/1997",
    "kirjanpitolain": "1336/1997",
    "tilintarkastuslaki": "1141/2015",
    "tilintarkastuslakia": "1141/2015",
    "tilintarkastuslain": "1141/2015",
    "osakeyhtiölaki": "624/2006",
    "osakeyhtiölakia": "624/2006",
    "osakeyhtiölain": "624/2006",
    "hankintalaki": "1397/2016",
    "hankintalakia": "1397/2016",
    "hankintalain": "1397/2016",
}

# Pattern for named law references without ID (e.g., "kirjanpitolakia")
NAMED_LAW_PATTERN = re.compile(
    r"\b(" + "|".join(KNOWN_LAWS.keys()) + r")\b",
    re.IGNORECASE
)

# v8.1: Exception keywords (improved)
EXCEPTION_KEYWORDS = [
    "poiketen",
    "poikkeuksena",
    "jollei",
    "ellei",
    "jos ei",
    "sen estämättä",
    "siitä huolimatta",
    "ilman rajoitusta",
    "lukuun ottamatta",
]

# v8.1: Definition keywords (improved - specific patterns)
DEFINITION_KEYWORDS = [
    "tarkoitetaan",
    "tässä laissa",
    "tässä luvussa",
    "käsitteellä",
    "määritelmä",
]


def parse_section_references(text: str) -> list[tuple[int, int | None, str]]:
    """
    Parse section references from legal text (v8.1 improved).
    
    Returns list of tuples: (section_num, moment_num_or_None, matched_text)
    """
    references: list[tuple[int, int | None, str]] = []
    found_sections: set[int] = set()
    found_section_moments: set[tuple[int, int]] = set()
    
    # 1. Find section + moment patterns first (most specific)
    for match in SECTION_MOMENT_PATTERN.finditer(text):
        section_num = int(match.group(1))
        moment_num = int(match.group(2))
        key = (section_num, moment_num)
        if key not in found_section_moments:
            references.append((section_num, moment_num, match.group(0)))
            found_section_moments.add(key)
            found_sections.add(section_num)
    
    # 2. Find section with declension (e.g., "6 §:n 2 momentissa" without moment)
    for match in SECTION_DECL_PATTERN.finditer(text):
        section_num = int(match.group(1))
        if section_num not in found_sections:
            references.append((section_num, None, match.group(0)))
            found_sections.add(section_num)
    
    # 3. Find chapter + section patterns
    for match in CHAPTER_SECTION_PATTERN.finditer(text):
        section_num = int(match.group(2))  # section is group 2
        if section_num not in found_sections:
            references.append((section_num, None, match.group(0)))
            found_sections.add(section_num)
    
    # 4. Find simple section references (avoid duplicates)
    for match in SIMPLE_SECTION_PATTERN.finditer(text):
        section_num = int(match.group(1))
        if section_num not in found_sections:
            references.append((section_num, None, match.group(0)))
            found_sections.add(section_num)
    
    return references


def is_exception_context(text: str, ref_position: int) -> bool:
    """Check if the reference is in an exception context."""
    # Look at text around the reference (100 chars before)
    start = max(0, ref_position - 100)
    context = text[start:ref_position].lower()
    
    for keyword in EXCEPTION_KEYWORDS:
        if keyword in context:
            return True
    return False


def is_definition_context(text: str) -> bool:
    """Check if the text is a definition context."""
    text_lower = text.lower()
    for keyword in DEFINITION_KEYWORDS:
        if keyword in text_lower:
            return True
    return False


def parse_external_law_references(text: str) -> list[tuple[str, str]]:
    """
    Parse external law references like "kirjanpitolain (1336/1997)".
    
    Returns list of tuples: (law_name, law_id)
    """
    references: list[tuple[str, str]] = []
    for match in EXTERNAL_LAW_PATTERN.finditer(text):
        law_name = match.group(1).lower()
        law_id = match.group(2)
        references.append((law_name, law_id))
    return references


def build_target_node_id(
    source_law_id: str,
    source_finlex_version: str,
    target_section: int,
    target_moment: int | None,
) -> str:
    """Build a target node_id for internal references."""
    if target_moment is not None:
        return f"{source_law_id}:{source_finlex_version}:{target_section}:{target_moment}"
    return f"{source_law_id}:{source_finlex_version}:{target_section}:*"


def load_all_moments() -> list[dict]:
    """Load all moment records from all law JSONL files."""
    all_moments: list[dict] = []
    
    # Kuntalaki (legacy location)
    kuntalaki_path = PROJECT_ROOT / "analysis_layer" / "json" / "kuntalaki_410-2015.jsonl"
    if kuntalaki_path.exists():
        with open(kuntalaki_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    all_moments.append(json.loads(line))
    
    # Other laws in laws/ directory
    laws_dir = PROJECT_ROOT / "laws"
    if laws_dir.exists():
        for law_dir in laws_dir.iterdir():
            if law_dir.is_dir():
                json_dir = law_dir / "analysis_layer" / "json"
                if json_dir.exists():
                    for jsonl_file in json_dir.glob("*.jsonl"):
                        with open(jsonl_file, "r", encoding="utf-8") as f:
                            for line in f:
                                if line.strip():
                                    all_moments.append(json.loads(line))
    
    return all_moments


def build_node_index(moments: list[dict]) -> dict[str, dict]:
    """Build an index of node_id -> moment data."""
    return {m["node_id"]: m for m in moments}


def build_section_index(moments: list[dict]) -> dict[tuple[str, int], list[str]]:
    """
    Build an index of (law_id, section_num) -> list of node_ids.
    Used for resolving references to sections without specific moments.
    """
    index: dict[tuple[str, int], list[str]] = {}
    for m in moments:
        key = (m["law_id"], m["section_num"])
        if key not in index:
            index[key] = []
        index[key].append(m["node_id"])
    return index


def process_moment(
    moment: dict,
    node_index: dict[str, dict],
    section_index: dict[tuple[str, int], list[str]],
) -> tuple[Node, list[Edge]]:
    """
    Process a single moment and extract its node and edges.
    """
    node: Node = {
        "node_id": moment["node_id"],
        "node_type": "MOMENT",
        "law_key": moment.get("law_key", ""),
        "section_num": moment.get("section_num"),
        "moment": moment.get("moment"),
        "section_title": moment.get("section_title", ""),
        "text": moment.get("text", ""),
    }
    
    edges: list[Edge] = []
    text = moment.get("text", "")
    law_id = moment["law_id"]
    finlex_version = moment.get("finlex_version", "")
    source_node_id = moment["node_id"]
    
    # Parse internal section references
    references = parse_section_references(text)
    for section_num, moment_num, matched_text in references:
        # Skip self-references
        if section_num == moment.get("section_num"):
            if moment_num is None or str(moment_num) == str(moment.get("moment")):
                continue
        
        # Determine edge type based on context
        ref_pos = text.find(matched_text)
        if is_exception_context(text, ref_pos):
            edge_type = "EXCEPTS"
        else:
            edge_type = "REFERS_TO"
        
        # Build target node_id
        target_node_id = build_target_node_id(
            law_id, finlex_version, section_num, moment_num
        )
        
        # Check if target exists (for moment-specific references)
        if moment_num is not None:
            if target_node_id not in node_index:
                # Try without finlex version (might be different version)
                target_node_id = f"{law_id}:*:{section_num}:{moment_num}"
        
        edges.append({
            "source": source_node_id,
            "target": target_node_id,
            "edge_type": edge_type,
            "context": matched_text,
        })
    
    # Parse external law references (with explicit ID)
    external_refs = parse_external_law_references(text)
    found_ext_law_ids: set[str] = set()
    for law_name, ext_law_id in external_refs:
        edges.append({
            "source": source_node_id,
            "target": f"external:{ext_law_id}",
            "edge_type": "REFERS_TO",
            "context": f"{law_name} ({ext_law_id})",
        })
        found_ext_law_ids.add(ext_law_id)
    
    # v8.1: Parse named law references (without explicit ID)
    for match in NAMED_LAW_PATTERN.finditer(text):
        law_name_found = match.group(1).lower()
        ext_law_id = KNOWN_LAWS.get(law_name_found)
        if ext_law_id and ext_law_id not in found_ext_law_ids:
            edges.append({
                "source": source_node_id,
                "target": f"external:{ext_law_id}",
                "edge_type": "REFERS_TO",
                "context": f"{law_name_found}",
            })
            found_ext_law_ids.add(ext_law_id)
    
    # Check if this is a definition
    if is_definition_context(text):
        # This moment defines something
        edges.append({
            "source": source_node_id,
            "target": f"definition:{source_node_id}",
            "edge_type": "DEFINES",
            "context": "Definition context detected",
        })
    
    return node, edges


def build_hierarchical_edges(moments: list[dict]) -> list[Edge]:
    """
    Build HAS_SECTION and HAS_MOMENT edges for the hierarchy.
    """
    edges: list[Edge] = []
    
    # Group moments by law and section
    law_sections: dict[str, set[int]] = {}
    for m in moments:
        law_key = m.get("law_key", m["law_id"])
        section_num = m.get("section_num")
        if law_key not in law_sections:
            law_sections[law_key] = set()
        if section_num is not None:
            law_sections[law_key].add(section_num)
    
    # Create LAW -> SECTION edges (one per unique section)
    for law_key, sections in law_sections.items():
        for section_num in sorted(sections):
            edges.append({
                "source": f"law:{law_key}",
                "target": f"section:{law_key}:{section_num}",
                "edge_type": "HAS_SECTION",
                "context": "",
            })
    
    # Create SECTION -> MOMENT edges
    for m in moments:
        law_key = m.get("law_key", m["law_id"])
        section_num = m.get("section_num")
        edges.append({
            "source": f"section:{law_key}:{section_num}",
            "target": m["node_id"],
            "edge_type": "HAS_MOMENT",
            "context": "",
        })
    
    return edges


def main() -> None:
    """Main function to build the structural legal graph."""
    print("=" * 60)
    print("v8: Building Structural Legal Graph")
    print("=" * 60)
    
    # Load all moments
    print("\nLoading moments from JSONL files...")
    moments = load_all_moments()
    print(f"  Loaded: {len(moments)} moments")
    
    if not moments:
        print("ERROR: No moments found!")
        sys.exit(1)
    
    # Build indices
    print("\nBuilding indices...")
    node_index = build_node_index(moments)
    section_index = build_section_index(moments)
    print(f"  Unique nodes: {len(node_index)}")
    print(f"  Unique sections: {len(section_index)}")
    
    # Process all moments
    print("\nProcessing moments and extracting references...")
    all_nodes: list[Node] = []
    all_edges: list[Edge] = []
    
    reference_count = 0
    exception_count = 0
    definition_count = 0
    external_count = 0
    
    for moment in moments:
        node, edges = process_moment(moment, node_index, section_index)
        all_nodes.append(node)
        
        for edge in edges:
            all_edges.append(edge)
            if edge["edge_type"] == "REFERS_TO":
                if edge["target"].startswith("external:"):
                    external_count += 1
                else:
                    reference_count += 1
            elif edge["edge_type"] == "EXCEPTS":
                exception_count += 1
            elif edge["edge_type"] == "DEFINES":
                definition_count += 1
    
    # Add hierarchical edges
    print("\nBuilding hierarchical edges...")
    hierarchical_edges = build_hierarchical_edges(moments)
    all_edges.extend(hierarchical_edges)
    
    print(f"\nEdge statistics:")
    print(f"  REFERS_TO (internal): {reference_count}")
    print(f"  REFERS_TO (external): {external_count}")
    print(f"  EXCEPTS: {exception_count}")
    print(f"  DEFINES: {definition_count}")
    print(f"  HAS_SECTION: {len([e for e in hierarchical_edges if e['edge_type'] == 'HAS_SECTION'])}")
    print(f"  HAS_MOMENT: {len([e for e in hierarchical_edges if e['edge_type'] == 'HAS_MOMENT'])}")
    print(f"  TOTAL edges: {len(all_edges)}")
    
    # Write output files
    graph_dir = PROJECT_ROOT / "graph"
    graph_dir.mkdir(exist_ok=True)
    
    nodes_path = graph_dir / "nodes.jsonl"
    edges_path = graph_dir / "edges.jsonl"
    
    print(f"\nWriting {nodes_path}...")
    with open(nodes_path, "w", encoding="utf-8") as f:
        for node in all_nodes:
            f.write(json.dumps(node, ensure_ascii=False) + "\n")
    
    print(f"Writing {edges_path}...")
    with open(edges_path, "w", encoding="utf-8") as f:
        for edge in all_edges:
            f.write(json.dumps(edge, ensure_ascii=False) + "\n")
    
    # Write summary
    summary = {
        "total_nodes": len(all_nodes),
        "total_edges": len(all_edges),
        "edge_types": {
            "REFERS_TO_internal": reference_count,
            "REFERS_TO_external": external_count,
            "EXCEPTS": exception_count,
            "DEFINES": definition_count,
            "HAS_SECTION": len([e for e in hierarchical_edges if e["edge_type"] == "HAS_SECTION"]),
            "HAS_MOMENT": len([e for e in hierarchical_edges if e["edge_type"] == "HAS_MOMENT"]),
        },
        "laws": list(set(m.get("law_key", m["law_id"]) for m in moments)),
    }
    
    summary_path = graph_dir / "graph_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\nGraph built successfully!")
    print(f"  Nodes: {nodes_path}")
    print(f"  Edges: {edges_path}")
    print(f"  Summary: {summary_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()

