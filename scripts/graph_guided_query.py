#!/usr/bin/env python3
"""
v8: Graph-guided Query

Combines v7.2 retrieval with graph expansion for enhanced answers.
Returns primary hit + supporting nodes + normipolku.

Usage:
    python scripts/graph_guided_query.py "kunnan tilinpäätöksen laatimisvelvollisuus"
    python scripts/graph_guided_query.py --interactive
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"Missing dependency: {e}")
    sys.exit(1)

from shared.query_rules.law_router import route_query, calculate_k_per_law
from scripts.graph_context_builder import GraphContextBuilder


# Law indices configuration (same as run_cross_law_eval.py)
LAW_INDICES = {
    "kuntalaki_410_2015": {
        "chroma_path": PROJECT_ROOT / "analysis_layer" / "embeddings" / "chroma_db",
        "collection_name": "kuntalaki",
    },
    "kirjanpitolaki_1336_1997": {
        "chroma_path": PROJECT_ROOT / "laws" / "kirjanpitolaki_1336_1997" / "analysis_layer" / "embeddings" / "chroma_db",
        "collection_name": "kirjanpitolaki",
    },
    "tilintarkastuslaki_1141_2015": {
        "chroma_path": PROJECT_ROOT / "laws" / "tilintarkastuslaki_1141_2015" / "analysis_layer" / "embeddings" / "chroma_db",
        "collection_name": "tilintarkastuslaki",
    },
    "hankintalaki_1397_2016": {
        "chroma_path": PROJECT_ROOT / "laws" / "hankintalaki_1397_2016" / "analysis_layer" / "embeddings" / "chroma_db",
        "collection_name": "hankintalaki",
    },
    "osakeyhtiolaki_624_2006": {
        "chroma_path": PROJECT_ROOT / "laws" / "osakeyhtiolaki_624_2006" / "analysis_layer" / "embeddings" / "chroma_db",
        "collection_name": "osakeyhtiolaki",
    },
    "kirjanpitoasetus_1339_1997": {
        "chroma_path": PROJECT_ROOT / "laws" / "kirjanpitoasetus_1339_1997" / "analysis_layer" / "embeddings" / "chroma_db",
        "collection_name": "kirjanpitoasetus",
    },
}

# Reranking parameters
ROUTER_BONUS = 0.02
MIN_SCORE = 0.50
K_TOTAL = 10

# v8.1: Law mismatch penalty for municipal context
LAW_MISMATCH_PENALTY = 0.03
_MUNICIPAL_ANCHORS = ["kunnan", "kunta", "kuntakonserni", "kuntalaki", "kuntalain"]


def load_indices() -> dict[str, Any]:
    """Load all available law indices."""
    indices: dict[str, Any] = {}
    for law_key, config in LAW_INDICES.items():
        chroma_path = config["chroma_path"]
        if chroma_path.exists():
            try:
                client = chromadb.PersistentClient(path=str(chroma_path))
                collection = client.get_collection(config["collection_name"])
                indices[law_key] = collection
            except Exception:
                pass
    return indices


def multi_law_query(
    query: str,
    indices: dict[str, Any],
    model: SentenceTransformer,
    total_k: int = K_TOTAL,
    min_score: float = MIN_SCORE,
) -> tuple[list[dict], float]:
    """
    Query multiple law indices and return merged results.
    
    Returns tuple of (results, latency_ms)
    """
    start_time = time.time()
    
    available_laws = list(indices.keys())
    weights = route_query(query, available_laws)
    
    k_per_law = calculate_k_per_law(weights, total_k, min_k=2)
    
    embedding = model.encode([query], normalize_embeddings=True)[0].tolist()
    
    # v8.1: Check for municipal context
    query_lower = query.lower()
    has_municipal = any(anchor in query_lower for anchor in _MUNICIPAL_ANCHORS)
    
    all_results: list[dict] = []
    top1_law = max(weights, key=weights.get) if weights else None
    
    for law_key, k in k_per_law.items():
        if law_key not in indices:
            continue
        
        collection = indices[law_key]
        results = collection.query(
            query_embeddings=[embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            score = 1 - dist
            
            # Apply router bonus
            if law_key == top1_law:
                score += ROUTER_BONUS
            
            # v8.1: Apply law-mismatch penalty for municipal context
            if has_municipal and law_key != "kuntalaki_410_2015":
                score -= LAW_MISMATCH_PENALTY
            
            if score >= min_score:
                all_results.append({
                    "law_key": law_key,
                    "score": score,
                    "section_num": meta.get("section_num", 0),
                    "section_id": meta.get("section_id", ""),
                    "moment": meta.get("moment", ""),
                    "section_title": meta.get("section_title", ""),
                    "node_id": meta.get("node_id", ""),
                    "text": doc,
                    "anchors": json.loads(meta.get("anchors", "[]")),
                })
    
    # Sort by score
    all_results.sort(key=lambda x: -x["score"])
    
    latency_ms = (time.time() - start_time) * 1000
    return all_results[:total_k], latency_ms


def format_graph_answer(result: dict, query: str) -> str:
    """Format the graph-guided answer."""
    lines: list[str] = []
    
    primary = result.get("primary_hit", {})
    supporting = result.get("supporting_nodes", [])
    
    lines.append("=" * 70)
    lines.append("GRAPH-GUIDED ANSWER")
    lines.append("=" * 70)
    
    lines.append(f"\nQUERY: {query}")
    
    # Primary source
    lines.append(f"\n--- PRIMARY SOURCE ---")
    law_key = primary.get("law_key", "")
    section = primary.get("section_num", "")
    moment = primary.get("moment", "")
    title = primary.get("section_title", "")
    score = primary.get("score", 0)
    
    lines.append(f"Law: {law_key}")
    lines.append(f"Section: {section} - {title}")
    lines.append(f"Moment: {moment}")
    lines.append(f"Score: {score:.4f}")
    lines.append(f"\nText:")
    lines.append(primary.get("text", ""))
    
    # Supporting nodes (exceptions, references)
    if supporting:
        lines.append(f"\n--- SUPPORTING CONTEXT ({len(supporting)} nodes) ---")
        
        # Group by relation type
        exceptions = [s for s in supporting if s["relation"] == "EXCEPTS"]
        references = [s for s in supporting if s["relation"] == "REFERS_TO"]
        definitions = [s for s in supporting if s["relation"] == "DEFINES"]
        
        if exceptions:
            lines.append("\nEXCEPTIONS (poikkeukset):")
            for exc in exceptions:
                lines.append(f"  - {exc['law_key']} {exc['section_num']}:{exc['moment']}")
                lines.append(f"    {exc['section_title']}")
                text_preview = exc["text"][:150] + "..." if len(exc["text"]) > 150 else exc["text"]
                lines.append(f"    {text_preview}")
        
        if references:
            lines.append("\nREFERENCES (viittaukset):")
            for ref in references:
                lines.append(f"  - {ref['law_key']} {ref['section_num']}:{ref['moment']}")
                lines.append(f"    {ref['section_title']}")
                text_preview = ref["text"][:150] + "..." if len(ref["text"]) > 150 else ref["text"]
                lines.append(f"    {text_preview}")
    
    # Normipolku
    if result.get("normipolku"):
        lines.append(f"\n--- NORMIPOLKU ---")
        for edge in result["normipolku"]:
            ext = " [external law]" if edge.get("external") else ""
            lines.append(f"  {edge['from']} --{edge['edge_type']}--> {edge['to']}{ext}")
    
    lines.append("\n" + "=" * 70)
    
    return "\n".join(lines)


def query_with_graph(
    query: str,
    indices: dict[str, Any],
    model: SentenceTransformer,
    graph_builder: GraphContextBuilder,
) -> dict:
    """
    Perform a graph-guided query.
    
    Returns dict with:
        - query
        - primary_hit
        - supporting_nodes
        - normipolku
        - latency_ms
    """
    # Step 1: Multi-law retrieval
    hits, retrieval_latency = multi_law_query(query, indices, model)
    
    if not hits:
        return {
            "query": query,
            "primary_hit": None,
            "supporting_nodes": [],
            "normipolku": [],
            "latency_ms": retrieval_latency,
        }
    
    # Step 2: Graph expansion on top-1
    start_graph = time.time()
    expanded = graph_builder.expand_context(hits[0], query)
    graph_latency = (time.time() - start_graph) * 1000
    
    return {
        "query": query,
        "primary_hit": expanded["primary"],
        "supporting_nodes": expanded["supporting_nodes"],
        "normipolku": expanded["normipolku"],
        "latency_ms": retrieval_latency + graph_latency,
        "retrieval_latency_ms": retrieval_latency,
        "graph_latency_ms": graph_latency,
    }


def interactive_mode(
    indices: dict[str, Any],
    model: SentenceTransformer,
    graph_builder: GraphContextBuilder,
) -> None:
    """Run interactive query mode."""
    print("\n" + "=" * 70)
    print("v8: Graph-guided Legal Query (Interactive)")
    print("Type 'quit' to exit")
    print("=" * 70)
    
    while True:
        try:
            query = input("\nQuery: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        
        if not query or query.lower() in ["quit", "exit", "q"]:
            break
        
        result = query_with_graph(query, indices, model, graph_builder)
        
        if result["primary_hit"]:
            print(format_graph_answer(result, query))
            print(f"\nLatency: {result['latency_ms']:.1f} ms")
            print(f"  - Retrieval: {result['retrieval_latency_ms']:.1f} ms")
            print(f"  - Graph: {result['graph_latency_ms']:.1f} ms")
        else:
            print("\nNo results found.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Graph-guided Legal Query")
    parser.add_argument("query", nargs="?", help="Query string")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    args = parser.parse_args()
    
    print("Loading indices...")
    indices = load_indices()
    print(f"  Loaded: {len(indices)} indices")
    
    print("Loading embedding model...")
    model = SentenceTransformer("BAAI/bge-m3")
    
    print("Initializing graph context builder...")
    graph_builder = GraphContextBuilder()
    
    if args.interactive:
        interactive_mode(indices, model, graph_builder)
    elif args.query:
        result = query_with_graph(args.query, indices, model, graph_builder)
        if result["primary_hit"]:
            print(format_graph_answer(result, args.query))
            print(f"\nLatency: {result['latency_ms']:.1f} ms")
        else:
            print("No results found.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

