#!/usr/bin/env python3
"""
v9: Build Document Graph from structured financial statement JSON.

This script converts a parsed financial statement (tilinpäätös) into a
navigable graph structure (nodes + edges).

Usage:
    python docs_layer/scripts/build_document_graph.py --input <parsed_json> --output <output_dir>
    
Input: Structured JSON from PDF parsing (parse_pdf.py)
Output: nodes.jsonl + edges.jsonl in output_dir
"""

import argparse
import json
from pathlib import Path
from typing import TypedDict


class DocNode(TypedDict):
    """Node in the document graph."""
    node_id: str
    node_type: str  # DOC, PAGE, SECTION, TABLE, ROW, CELL, PARA, METRIC
    city: str
    year: int
    title: str
    text: str
    page_num: int | None
    parent_id: str | None
    metadata: dict


class DocEdge(TypedDict):
    """Edge in the document graph."""
    source: str
    target: str
    edge_type: str  # HAS_PAGE, HAS_SECTION, HAS_TABLE, HAS_PARA, NEXT, REFERS_TO, DERIVED_FROM
    context: str


def generate_node_id(city: str, year: int, node_type: str, path: str) -> str:
    """Generate a unique node_id for a document node."""
    return f"{city}:{year}:{node_type}:{path}"


def parse_structured_json(input_path: Path) -> dict:
    """
    Load and validate structured JSON from PDF parsing.
    
    Expected format:
    {
        "city": "lapua",
        "year": 2023,
        "title": "Tilinpäätös 2023",
        "pages": [
            {
                "page_num": 1,
                "sections": [
                    {
                        "title": "Toimintakertomus",
                        "level": 1,
                        "paragraphs": ["..."],
                        "tables": [
                            {
                                "title": "Tuloslaskelma",
                                "rows": [
                                    {"cells": ["Toimintatuotot", "1000", "1100"]}
                                ]
                            }
                        ],
                        "subsections": [...]
                    }
                ]
            }
        ],
        "metrics": [
            {"name": "vuosikate", "value": 1234567, "unit": "EUR", "page": 15}
        ]
    }
    """
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Validate required fields
    required = ["city", "year", "title", "pages"]
    for field in required:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
    
    return data


def build_graph(data: dict) -> tuple[list[DocNode], list[DocEdge]]:
    """
    Build document graph from structured data.
    
    Returns:
        Tuple of (nodes, edges)
    """
    nodes: list[DocNode] = []
    edges: list[DocEdge] = []
    
    city = data["city"]
    year = data["year"]
    
    # Create DOC node (root)
    doc_id = generate_node_id(city, year, "DOC", "root")
    nodes.append({
        "node_id": doc_id,
        "node_type": "DOC",
        "city": city,
        "year": year,
        "title": data["title"],
        "text": "",
        "page_num": None,
        "parent_id": None,
        "metadata": {"total_pages": len(data.get("pages", []))},
    })
    
    prev_page_id = None
    
    # Process pages
    for page_data in data.get("pages", []):
        page_num = page_data["page_num"]
        page_id = generate_node_id(city, year, "PAGE", str(page_num))
        
        nodes.append({
            "node_id": page_id,
            "node_type": "PAGE",
            "city": city,
            "year": year,
            "title": f"Sivu {page_num}",
            "text": "",
            "page_num": page_num,
            "parent_id": doc_id,
            "metadata": {},
        })
        
        edges.append({
            "source": doc_id,
            "target": page_id,
            "edge_type": "HAS_PAGE",
            "context": f"Page {page_num}",
        })
        
        # NEXT edge between pages
        if prev_page_id:
            edges.append({
                "source": prev_page_id,
                "target": page_id,
                "edge_type": "NEXT",
                "context": "Sequential pages",
            })
        prev_page_id = page_id
        
        # Process sections on this page
        section_nodes, section_edges = _process_sections(
            city, year, page_id, page_num, page_data.get("sections", []), ""
        )
        nodes.extend(section_nodes)
        edges.extend(section_edges)
    
    # Process metrics (if any)
    for metric_data in data.get("metrics", []):
        metric_id = generate_node_id(city, year, "METRIC", metric_data["name"])
        nodes.append({
            "node_id": metric_id,
            "node_type": "METRIC",
            "city": city,
            "year": year,
            "title": metric_data["name"],
            "text": f"{metric_data['value']} {metric_data.get('unit', '')}",
            "page_num": metric_data.get("page"),
            "parent_id": doc_id,
            "metadata": {
                "value": metric_data["value"],
                "unit": metric_data.get("unit", ""),
            },
        })
    
    return nodes, edges


def _process_sections(
    city: str,
    year: int,
    parent_id: str,
    page_num: int,
    sections: list[dict],
    path_prefix: str,
) -> tuple[list[DocNode], list[DocEdge]]:
    """Process sections recursively."""
    nodes: list[DocNode] = []
    edges: list[DocEdge] = []
    
    prev_section_id = None
    
    for i, section in enumerate(sections):
        # Generate section path
        section_slug = section.get("title", f"section_{i}").lower()
        section_slug = section_slug.replace(" ", "_")[:30]
        section_path = f"{path_prefix}:{section_slug}" if path_prefix else section_slug
        
        section_id = generate_node_id(city, year, "SECTION", section_path)
        
        # Combine paragraphs into text
        text = "\n".join(section.get("paragraphs", []))
        
        nodes.append({
            "node_id": section_id,
            "node_type": "SECTION",
            "city": city,
            "year": year,
            "title": section.get("title", ""),
            "text": text,
            "page_num": page_num,
            "parent_id": parent_id,
            "metadata": {"level": section.get("level", 1)},
        })
        
        edges.append({
            "source": parent_id,
            "target": section_id,
            "edge_type": "HAS_SECTION",
            "context": section.get("title", ""),
        })
        
        # NEXT edge between sections
        if prev_section_id:
            edges.append({
                "source": prev_section_id,
                "target": section_id,
                "edge_type": "NEXT",
                "context": "Sequential sections",
            })
        prev_section_id = section_id
        
        # Process paragraphs as separate nodes (optional, for fine-grained indexing)
        for j, para in enumerate(section.get("paragraphs", [])):
            if len(para.strip()) > 50:  # Only meaningful paragraphs
                para_id = generate_node_id(city, year, "PARA", f"{section_path}:p{j}")
                nodes.append({
                    "node_id": para_id,
                    "node_type": "PARA",
                    "city": city,
                    "year": year,
                    "title": "",
                    "text": para,
                    "page_num": page_num,
                    "parent_id": section_id,
                    "metadata": {},
                })
                edges.append({
                    "source": section_id,
                    "target": para_id,
                    "edge_type": "HAS_PARA",
                    "context": f"Paragraph {j}",
                })
        
        # Process tables
        for k, table in enumerate(section.get("tables", [])):
            table_title = table.get("title", f"table_{k}")
            table_slug = table_title.lower().replace(" ", "_")[:20]
            table_id = generate_node_id(city, year, "TABLE", f"{section_path}:{table_slug}")
            
            nodes.append({
                "node_id": table_id,
                "node_type": "TABLE",
                "city": city,
                "year": year,
                "title": table_title,
                "text": "",
                "page_num": page_num,
                "parent_id": section_id,
                "metadata": {"row_count": len(table.get("rows", []))},
            })
            
            edges.append({
                "source": section_id,
                "target": table_id,
                "edge_type": "HAS_TABLE",
                "context": table_title,
            })
            
            # Process rows
            for r, row in enumerate(table.get("rows", [])):
                row_id = generate_node_id(city, year, "ROW", f"{section_path}:{table_slug}:r{r}")
                cells = row.get("cells", [])
                row_text = " | ".join(str(c) for c in cells)
                
                nodes.append({
                    "node_id": row_id,
                    "node_type": "ROW",
                    "city": city,
                    "year": year,
                    "title": cells[0] if cells else "",
                    "text": row_text,
                    "page_num": page_num,
                    "parent_id": table_id,
                    "metadata": {"cells": cells},
                })
                
                edges.append({
                    "source": table_id,
                    "target": row_id,
                    "edge_type": "HAS_ROW",
                    "context": f"Row {r}",
                })
        
        # Process subsections recursively
        sub_nodes, sub_edges = _process_sections(
            city, year, section_id, page_num,
            section.get("subsections", []), section_path
        )
        nodes.extend(sub_nodes)
        edges.extend(sub_edges)
    
    return nodes, edges


def write_graph(nodes: list[DocNode], edges: list[DocEdge], output_dir: Path) -> None:
    """Write graph to JSONL files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    nodes_path = output_dir / "nodes.jsonl"
    edges_path = output_dir / "edges.jsonl"
    
    with open(nodes_path, "w", encoding="utf-8") as f:
        for node in nodes:
            f.write(json.dumps(node, ensure_ascii=False) + "\n")
    
    with open(edges_path, "w", encoding="utf-8") as f:
        for edge in edges:
            f.write(json.dumps(edge, ensure_ascii=False) + "\n")
    
    print(f"Wrote {len(nodes)} nodes to {nodes_path}")
    print(f"Wrote {len(edges)} edges to {edges_path}")
    
    # Write summary
    summary = {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "node_types": {},
        "edge_types": {},
    }
    
    for node in nodes:
        nt = node["node_type"]
        summary["node_types"][nt] = summary["node_types"].get(nt, 0) + 1
    
    for edge in edges:
        et = edge["edge_type"]
        summary["edge_types"][et] = summary["edge_types"].get(et, 0) + 1
    
    summary_path = output_dir / "graph_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"Summary: {summary_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build document graph from structured JSON")
    parser.add_argument("--input", "-i", required=True, help="Path to structured JSON")
    parser.add_argument("--output", "-o", required=True, help="Output directory for graph")
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_dir = Path(args.output)
    
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        return
    
    print(f"Loading structured JSON: {input_path}")
    data = parse_structured_json(input_path)
    
    print(f"Building document graph for {data['city']} {data['year']}...")
    nodes, edges = build_graph(data)
    
    write_graph(nodes, edges, output_dir)
    
    print("\nDone!")


if __name__ == "__main__":
    main()

