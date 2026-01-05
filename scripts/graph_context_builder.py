#!/usr/bin/env python3
"""
v8: Graph-guided Context Builder

Expands retrieval results using the structural legal graph.
Adds references, exceptions, and definitions to the context.

Usage:
    from scripts.graph_context_builder import GraphContextBuilder
    
    builder = GraphContextBuilder()
    expanded = builder.expand_context(primary_hits, query)
"""

import json
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


class SupportingNode(TypedDict):
    """A supporting node added via graph expansion."""
    node_id: str
    node_type: str
    law_key: str
    section_num: int | None
    moment: int | str | None
    section_title: str
    text: str
    relation: str  # REFERS_TO, EXCEPTS, DEFINES
    hop_distance: int
    score: float
    path: list[str]  # Path from primary to this node


class ExpandedContext(TypedDict):
    """Result of graph expansion."""
    primary: dict  # Original retrieval hit
    supporting_nodes: list[SupportingNode]
    normipolku: list[dict]  # The norm path (edges traversed)


class GraphContextBuilder:
    """Builds expanded context using the structural legal graph."""
    
    # Priority order for edge types (higher = more important)
    EDGE_PRIORITY = {
        "EXCEPTS": 3,      # Exceptions are highest priority
        "REFERS_TO": 2,    # References are important
        "DEFINES": 1,      # Definitions are useful context
    }
    
    # Score decay per hop
    DECAY_PER_HOP = 0.05
    
    # Limits
    MAX_HOPS = 2
    MAX_NODES_ADDED = 5  # v8.1: reduced for better focus
    
    # v8.1: Definition/Exception trigger keywords
    DEFINITION_TRIGGERS = ["määritelmä", "tarkoitetaan", "tässä laissa", "käsitteellä"]
    EXCEPTION_TRIGGERS = ["poiketen", "poikkeuksena", "jollei", "ellei", "siitä huolimatta"]
    
    def __init__(self) -> None:
        """Initialize the graph context builder."""
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        self.adj: dict[str, list[Edge]] = {}
        self.rev_adj: dict[str, list[Edge]] = {}
        self._loaded = False
    
    def _load_graph(self) -> None:
        """Load the graph from disk."""
        if self._loaded:
            return
        
        nodes_path = GRAPH_DIR / "nodes.jsonl"
        edges_path = GRAPH_DIR / "edges.jsonl"
        
        if not nodes_path.exists() or not edges_path.exists():
            raise FileNotFoundError(
                "Graph files not found. Run build_structural_legal_graph.py first."
            )
        
        with open(nodes_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    node = json.loads(line)
                    self.nodes[node["node_id"]] = node
        
        with open(edges_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    edge = json.loads(line)
                    self.edges.append(edge)
                    
                    # Build adjacency
                    if edge["source"] not in self.adj:
                        self.adj[edge["source"]] = []
                    self.adj[edge["source"]].append(edge)
                    
                    # Build reverse adjacency
                    if edge["target"] not in self.rev_adj:
                        self.rev_adj[edge["target"]] = []
                    self.rev_adj[edge["target"]].append(edge)
        
        self._loaded = True
    
    def _get_section_sibling_ids(self, node_id: str) -> list[str]:
        """
        Get all moment node_ids in the same section.
        
        If node_id is 410/2015:fin@20230780:8:3, this returns all
        410/2015:fin@20230780:8:* node_ids (8:1, 8:2, 8:3, etc.)
        """
        if node_id not in self.nodes:
            return []
        
        node = self.nodes[node_id]
        law_key = node.get("law_key", "")
        section_num = node.get("section_num")
        
        if section_num is None:
            return []
        
        siblings = []
        for nid, n in self.nodes.items():
            if n.get("law_key") == law_key and n.get("section_num") == section_num:
                siblings.append(nid)
        return siblings
    
    def _get_neighbors(
        self,
        node_id: str,
        max_hops: int = MAX_HOPS,
    ) -> list[tuple[str, Edge, int, list[str]]]:
        """
        Get neighbors of a node up to max_hops.
        
        v8.1: Also searches neighbors of section siblings (other moments
        in the same section), since references often target specific moments
        but apply to the whole section context.
        
        Returns list of (neighbor_id, edge, hop_distance, path)
        """
        self._load_graph()
        
        neighbors: list[tuple[str, Edge, int, list[str]]] = []
        
        # v8.1: Start with current node AND its section siblings
        sibling_ids = self._get_section_sibling_ids(node_id)
        if not sibling_ids:
            sibling_ids = [node_id]
        
        visited: set[str] = set(sibling_ids)
        
        # BFS with path tracking - start from all siblings
        queue: list[tuple[str, int, list[str]]] = [
            (sid, 0, [node_id]) for sid in sibling_ids
        ]
        
        while queue:
            current, hop, path = queue.pop(0)
            
            if hop >= max_hops:
                continue
            
            # Outgoing edges (we follow references from this node)
            for edge in self.adj.get(current, []):
                # Skip hierarchical edges for expansion
                if edge["edge_type"] in ["HAS_SECTION", "HAS_MOMENT"]:
                    continue
                
                target = edge["target"]
                if target not in visited:
                    visited.add(target)
                    new_path = path + [target]
                    neighbors.append((target, edge, hop + 1, new_path))
                    queue.append((target, hop + 1, new_path))
            
            # Incoming EXCEPTS edges (we want to know what exceptions apply)
            for edge in self.rev_adj.get(current, []):
                if edge["edge_type"] == "EXCEPTS":
                    source = edge["source"]
                    if source not in visited:
                        visited.add(source)
                        new_path = path + [source]
                        neighbors.append((source, edge, hop + 1, new_path))
                        queue.append((source, hop + 1, new_path))
        
        return neighbors
    
    def _score_neighbor(
        self,
        primary_score: float,
        edge: Edge,
        hop_distance: int,
    ) -> float:
        """Calculate score for a neighbor node."""
        # Start with primary score minus decay
        score = primary_score - (self.DECAY_PER_HOP * hop_distance)
        
        # Boost based on edge type priority
        edge_type = edge["edge_type"]
        priority = self.EDGE_PRIORITY.get(edge_type, 0)
        score += 0.01 * priority
        
        return max(0.0, score)
    
    def expand_context(
        self,
        primary_hit: dict,
        query: str | None = None,
    ) -> ExpandedContext:
        """
        Expand context for a primary retrieval hit using the graph.
        
        Args:
            primary_hit: The primary retrieval result (must have 'node_id' and 'score')
            query: Optional query for relevance filtering
            
        Returns:
            ExpandedContext with primary hit and supporting nodes
        """
        self._load_graph()
        
        node_id = primary_hit.get("node_id", "")
        primary_score = primary_hit.get("score", 0.5)
        
        # Find neighbors
        neighbors = self._get_neighbors(node_id, self.MAX_HOPS)
        
        # Build supporting nodes
        supporting: list[SupportingNode] = []
        normipolku: list[dict] = []
        
        for neighbor_id, edge, hop_distance, path in neighbors:
            # Skip external references for now
            if neighbor_id.startswith("external:"):
                normipolku.append({
                    "from": edge["source"],
                    "to": neighbor_id,
                    "edge_type": edge["edge_type"],
                    "context": edge["context"],
                    "external": True,
                })
                continue
            
            # Skip definition placeholders
            if neighbor_id.startswith("definition:"):
                continue
            
            # Get node data
            node = self.nodes.get(neighbor_id)
            if node is None:
                # Try to resolve wildcard references
                if ":*:" in neighbor_id:
                    continue  # Skip unresolved wildcards
                continue
            
            # Calculate score
            score = self._score_neighbor(primary_score, edge, hop_distance)
            
            supporting.append({
                "node_id": neighbor_id,
                "node_type": node["node_type"],
                "law_key": node["law_key"],
                "section_num": node.get("section_num"),
                "moment": node.get("moment"),
                "section_title": node.get("section_title", ""),
                "text": node["text"],
                "relation": edge["edge_type"],
                "hop_distance": hop_distance,
                "score": score,
                "path": path,
            })
            
            normipolku.append({
                "from": edge["source"],
                "to": neighbor_id,
                "edge_type": edge["edge_type"],
                "context": edge["context"],
                "external": False,
            })
        
        # v8.1: 2-phase support budget
        # Phase 1: Mandatory categories (EXCEPTS, DEFINES if triggered)
        mandatory: list[SupportingNode] = []
        optional: list[SupportingNode] = []
        
        # Check if query triggers definition lookup
        query_lower = (query or "").lower()
        needs_definition = any(t in query_lower for t in self.DEFINITION_TRIGGERS)
        
        for sn in supporting:
            if sn["relation"] == "EXCEPTS":
                mandatory.append(sn)
            elif sn["relation"] == "DEFINES" and needs_definition:
                mandatory.append(sn)
            else:
                optional.append(sn)
        
        # Phase 2: Fill remaining budget with optional by priority
        optional.sort(
            key=lambda x: (
                -self.EDGE_PRIORITY.get(x["relation"], 0),
                -x["score"],
            )
        )
        
        # Take best from each category for mandatory (max 1 EXCEPTS, max 1 DEFINES)
        final_mandatory: list[SupportingNode] = []
        has_excepts = False
        has_defines = False
        for sn in mandatory:
            if sn["relation"] == "EXCEPTS" and not has_excepts:
                final_mandatory.append(sn)
                has_excepts = True
            elif sn["relation"] == "DEFINES" and not has_defines:
                final_mandatory.append(sn)
                has_defines = True
        
        # Combine and limit
        final_supporting = final_mandatory + optional
        final_supporting = final_supporting[:self.MAX_NODES_ADDED]
        
        return {
            "primary": primary_hit,
            "supporting_nodes": final_supporting,
            "normipolku": normipolku,
        }
    
    def expand_multiple(
        self,
        hits: list[dict],
        query: str | None = None,
        top_k: int = 3,
    ) -> list[ExpandedContext]:
        """
        Expand context for multiple retrieval hits.
        
        Args:
            hits: List of retrieval results
            query: Optional query for relevance filtering
            top_k: Number of primary hits to expand (default: 3)
            
        Returns:
            List of ExpandedContext for each primary hit
        """
        results: list[ExpandedContext] = []
        
        for hit in hits[:top_k]:
            expanded = self.expand_context(hit, query)
            results.append(expanded)
        
        return results
    
    def format_normipolku(self, expanded: ExpandedContext) -> str:
        """
        Format the normipolku (norm path) as a readable string.
        """
        primary = expanded["primary"]
        lines: list[str] = []
        
        lines.append(f"PRIMARY: {primary.get('node_id', '')}")
        lines.append(f"  Section: {primary.get('section_num', '')} - {primary.get('section_title', '')}")
        
        if expanded["supporting_nodes"]:
            lines.append("\nSUPPORTING NODES:")
            for sn in expanded["supporting_nodes"]:
                rel = sn["relation"]
                hop = sn["hop_distance"]
                lines.append(f"  [{rel}] (hop {hop}) {sn['node_id']}")
                lines.append(f"    Section: {sn.get('section_num', '')} - {sn.get('section_title', '')}")
                text_preview = sn["text"][:100] + "..." if len(sn["text"]) > 100 else sn["text"]
                lines.append(f"    Text: {text_preview}")
        
        if expanded["normipolku"]:
            lines.append("\nNORMIPOLKU (edges):")
            for edge in expanded["normipolku"]:
                ext = " [external]" if edge.get("external") else ""
                lines.append(f"  {edge['from']} --{edge['edge_type']}--> {edge['to']}{ext}")
        
        return "\n".join(lines)


def main() -> None:
    """Test the graph context builder."""
    print("=" * 60)
    print("v8: Graph Context Builder Test")
    print("=" * 60)
    
    builder = GraphContextBuilder()
    
    # Test with a sample hit
    test_hit = {
        "node_id": "410/2015:fin@20230780:6:1",
        "score": 0.72,
        "law_key": "kuntalaki_410_2015",
        "section_num": 6,
        "moment": 1,
        "section_title": "Kuntakonserni ja kunnan toiminta",
        "text": "Yhteiso, jossa kunnalla on kirjanpitolain...",
    }
    
    print(f"\nExpanding context for: {test_hit['node_id']}")
    expanded = builder.expand_context(test_hit)
    
    print(f"\n{builder.format_normipolku(expanded)}")
    
    print("\n" + "=" * 60)
    print(f"Found {len(expanded['supporting_nodes'])} supporting nodes")
    print(f"Found {len(expanded['normipolku'])} edges in normipolku")
    print("=" * 60)


if __name__ == "__main__":
    main()

