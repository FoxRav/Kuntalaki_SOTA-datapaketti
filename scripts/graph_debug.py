#!/usr/bin/env python3
"""
v8: Graph Debug CLI

Query the structural legal graph to inspect nodes and their neighbors.

Usage:
    python scripts/graph_debug.py --node <node_id> --hops <1|2>
    python scripts/graph_debug.py --section <section_num> --law <law_key>
    python scripts/graph_debug.py --stats
    
Examples:
    python scripts/graph_debug.py --node "410/2015:fin@20230780:6:1" --hops 2
    python scripts/graph_debug.py --section 113 --law kuntalaki_410_2015
    python scripts/graph_debug.py --stats
"""

import argparse
import json
import sys
from pathlib import Path
from typing import TypedDict

PROJECT_ROOT = Path(__file__).parent.parent
GRAPH_DIR = PROJECT_ROOT / "graph"


class Node(TypedDict):
    node_id: str
    node_type: str
    law_key: str
    section_num: int | None
    moment: int | str | None
    section_title: str
    text: str


class Edge(TypedDict):
    source: str
    target: str
    edge_type: str
    context: str


def load_graph() -> tuple[dict[str, Node], list[Edge]]:
    """Load nodes and edges from JSONL files."""
    nodes: dict[str, Node] = {}
    edges: list[Edge] = []
    
    nodes_path = GRAPH_DIR / "nodes.jsonl"
    edges_path = GRAPH_DIR / "edges.jsonl"
    
    if not nodes_path.exists() or not edges_path.exists():
        print("ERROR: Graph files not found. Run build_structural_legal_graph.py first.")
        sys.exit(1)
    
    with open(nodes_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                node = json.loads(line)
                nodes[node["node_id"]] = node
    
    with open(edges_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                edges.append(json.loads(line))
    
    return nodes, edges


def build_adjacency(edges: list[Edge]) -> dict[str, list[Edge]]:
    """Build adjacency list from edges (source -> edges)."""
    adj: dict[str, list[Edge]] = {}
    for edge in edges:
        if edge["source"] not in adj:
            adj[edge["source"]] = []
        adj[edge["source"]].append(edge)
    return adj


def build_reverse_adjacency(edges: list[Edge]) -> dict[str, list[Edge]]:
    """Build reverse adjacency list (target -> edges)."""
    adj: dict[str, list[Edge]] = {}
    for edge in edges:
        if edge["target"] not in adj:
            adj[edge["target"]] = []
        adj[edge["target"]].append(edge)
    return adj


def find_neighbors(
    node_id: str,
    adj: dict[str, list[Edge]],
    rev_adj: dict[str, list[Edge]],
    hops: int = 1,
) -> dict[str, list[tuple[Edge, int]]]:
    """
    Find neighbors of a node up to N hops.
    
    Returns dict of node_id -> list of (edge, hop_distance)
    """
    visited: set[str] = {node_id}
    result: dict[str, list[tuple[Edge, int]]] = {}
    
    current_level: set[str] = {node_id}
    
    for hop in range(1, hops + 1):
        next_level: set[str] = set()
        
        for current_node in current_level:
            # Outgoing edges
            for edge in adj.get(current_node, []):
                target = edge["target"]
                if target not in visited:
                    visited.add(target)
                    next_level.add(target)
                    if target not in result:
                        result[target] = []
                    result[target].append((edge, hop))
            
            # Incoming edges (for reverse traversal)
            for edge in rev_adj.get(current_node, []):
                source = edge["source"]
                if source not in visited:
                    visited.add(source)
                    next_level.add(source)
                    if source not in result:
                        result[source] = []
                    result[source].append((edge, hop))
        
        current_level = next_level
    
    return result


def format_node(node: Node | None, node_id: str) -> str:
    """Format a node for display."""
    if node is None:
        return f"  [NOT FOUND] {node_id}"
    
    text_preview = node["text"][:100] + "..." if len(node["text"]) > 100 else node["text"]
    return (
        f"  [{node['node_type']}] {node['node_id']}\n"
        f"    Section: {node.get('section_num')} - {node.get('section_title', '')}\n"
        f"    Moment: {node.get('moment')}\n"
        f"    Text: {text_preview}"
    )


def cmd_query_node(args: argparse.Namespace) -> None:
    """Query a specific node and its neighbors."""
    nodes, edges = load_graph()
    adj = build_adjacency(edges)
    rev_adj = build_reverse_adjacency(edges)
    
    node_id = args.node
    hops = args.hops
    
    print(f"\n{'='*60}")
    print(f"Graph Query: {node_id} (hops={hops})")
    print(f"{'='*60}")
    
    # Find the node
    if node_id not in nodes:
        # Try partial match
        matches = [nid for nid in nodes if node_id in nid]
        if matches:
            print(f"\nNode not found. Did you mean one of these?")
            for m in matches[:10]:
                print(f"  - {m}")
            return
        print(f"\nNode not found: {node_id}")
        return
    
    node = nodes[node_id]
    print(f"\n--- Primary Node ---")
    print(format_node(node, node_id))
    
    # Find neighbors
    neighbors = find_neighbors(node_id, adj, rev_adj, hops)
    
    # Group by edge type and hop
    by_type: dict[str, list[tuple[str, Edge, int]]] = {}
    for neighbor_id, edge_list in neighbors.items():
        for edge, hop in edge_list:
            edge_type = edge["edge_type"]
            if edge_type not in by_type:
                by_type[edge_type] = []
            by_type[edge_type].append((neighbor_id, edge, hop))
    
    # Display by type
    for edge_type in ["REFERS_TO", "EXCEPTS", "DEFINES", "HAS_MOMENT", "HAS_SECTION"]:
        if edge_type in by_type:
            print(f"\n--- {edge_type} ({len(by_type[edge_type])}) ---")
            for neighbor_id, edge, hop in sorted(by_type[edge_type], key=lambda x: x[2]):
                direction = "->" if edge["source"] == node_id else "<-"
                neighbor_node = nodes.get(neighbor_id)
                
                print(f"\n  [Hop {hop}] {direction} {neighbor_id}")
                print(f"    Context: {edge['context']}")
                if neighbor_node:
                    text_preview = neighbor_node["text"][:80] + "..." if len(neighbor_node["text"]) > 80 else neighbor_node["text"]
                    print(f"    Text: {text_preview}")


def cmd_query_section(args: argparse.Namespace) -> None:
    """Query all moments in a section."""
    nodes, edges = load_graph()
    
    section_num = args.section
    law_key = args.law
    
    print(f"\n{'='*60}")
    print(f"Section Query: {law_key} - {section_num}")
    print(f"{'='*60}")
    
    # Find all moments in this section
    matching: list[Node] = []
    for node in nodes.values():
        if (
            node.get("section_num") == section_num
            and (law_key is None or law_key in node.get("law_key", ""))
        ):
            matching.append(node)
    
    if not matching:
        print(f"\nNo moments found for section {section_num}")
        return
    
    matching.sort(key=lambda n: (n.get("moment", 0)))
    
    print(f"\nFound {len(matching)} moments:")
    for node in matching:
        print(f"\n{format_node(node, node['node_id'])}")
    
    # Find references TO this section
    adj = build_adjacency(edges)
    rev_adj = build_reverse_adjacency(edges)
    
    incoming: list[tuple[str, Edge]] = []
    for node in matching:
        for edge in rev_adj.get(node["node_id"], []):
            if edge["edge_type"] in ["REFERS_TO", "EXCEPTS"]:
                incoming.append((edge["source"], edge))
    
    if incoming:
        print(f"\n--- Incoming References ({len(incoming)}) ---")
        for source_id, edge in incoming[:20]:  # Limit to 20
            source_node = nodes.get(source_id)
            source_info = ""
            if source_node:
                source_info = f" ({source_node.get('section_title', '')})"
            print(f"  [{edge['edge_type']}] {source_id}{source_info}")
            print(f"    Context: {edge['context']}")


def cmd_stats(args: argparse.Namespace) -> None:
    """Show graph statistics."""
    summary_path = GRAPH_DIR / "graph_summary.json"
    if summary_path.exists():
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)
        
        print(f"\n{'='*60}")
        print("Graph Statistics")
        print(f"{'='*60}")
        print(f"\nTotal nodes: {summary['total_nodes']}")
        print(f"Total edges: {summary['total_edges']}")
        print(f"\nEdge types:")
        for edge_type, count in summary["edge_types"].items():
            print(f"  {edge_type}: {count}")
        print(f"\nLaws:")
        for law in summary["laws"]:
            print(f"  - {law}")
    else:
        print("ERROR: graph_summary.json not found")


def main() -> None:
    parser = argparse.ArgumentParser(description="Graph Debug CLI")
    subparsers = parser.add_subparsers(dest="command")
    
    # If no subcommand, check for direct args
    parser.add_argument("--node", type=str, help="Node ID to query")
    parser.add_argument("--hops", type=int, default=1, help="Number of hops (default: 1)")
    parser.add_argument("--section", type=int, help="Section number to query")
    parser.add_argument("--law", type=str, help="Law key filter")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    
    args = parser.parse_args()
    
    if args.stats:
        cmd_stats(args)
    elif args.node:
        cmd_query_node(args)
    elif args.section:
        cmd_query_section(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

