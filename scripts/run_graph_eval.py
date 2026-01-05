#!/usr/bin/env python3
"""
v8: Graph-needed Eval

Evaluates graph expansion effectiveness on questions requiring references/exceptions.

Metrics:
- PRIMARY_PASS: Primary hit matches expected
- GRAPH_PATH_PASS: Graph expansion finds expected references/exceptions
- SUPPORT_PASS: Supporting nodes contain expected content

Usage:
    python scripts/run_graph_eval.py
"""

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


# Law indices configuration
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
) -> list[dict]:
    """Query multiple law indices and return merged results (v8.1)."""
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
                })
    
    all_results.sort(key=lambda x: -x["score"])
    return all_results[:total_k]


def evaluate_question(
    question: dict,
    indices: dict[str, Any],
    model: SentenceTransformer,
    graph_builder: GraphContextBuilder,
) -> dict:
    """Evaluate a single graph-needed question."""
    query = question.get("query", "")
    qid = question.get("id", "")
    expected_primary = question.get("expected_primary", {})
    expected_refs = question.get("expected_references", [])
    expected_exceptions = question.get("expected_exceptions", [])
    
    start_time = time.time()
    
    # Step 1: Retrieval
    hits = multi_law_query(query, indices, model)
    
    if not hits:
        return {
            "id": qid,
            "query": query,
            "primary_pass": False,
            "graph_path_pass": False,
            "support_pass": False,
            "latency_ms": (time.time() - start_time) * 1000,
            "error": "No results",
        }
    
    # Step 2: Graph expansion
    expanded = graph_builder.expand_context(hits[0], query)
    
    latency_ms = (time.time() - start_time) * 1000
    
    # Evaluate PRIMARY_PASS
    primary_hit = hits[0]
    primary_pass = True
    
    if expected_primary.get("law_key"):
        if primary_hit["law_key"] != expected_primary["law_key"]:
            primary_pass = False
    
    if expected_primary.get("section_num"):
        if primary_hit["section_num"] != expected_primary["section_num"]:
            primary_pass = False
    
    if expected_primary.get("moment"):
        if str(primary_hit["moment"]) != str(expected_primary["moment"]):
            primary_pass = False
    
    # Evaluate GRAPH_PATH_PASS (do we find expected references in normipolku?)
    normipolku = expanded.get("normipolku", [])
    graph_path_pass = True
    
    # Check if we have any outgoing references when expected
    if expected_refs:
        found_refs = [
            edge for edge in normipolku
            if edge["edge_type"] in ["REFERS_TO", "EXCEPTS"]
        ]
        if not found_refs:
            graph_path_pass = False
    
    # Evaluate SUPPORT_PASS (do supporting nodes contain expected content?)
    supporting = expanded.get("supporting_nodes", [])
    support_pass = True
    
    if expected_refs or expected_exceptions:
        if not supporting:
            support_pass = False
    
    # Check for external law references if expected
    for ref in expected_refs:
        if ref.get("law_key") and ref["law_key"] != primary_hit["law_key"]:
            # Look for external reference in normipolku
            ext_refs = [
                edge for edge in normipolku
                if edge.get("external") or "external:" in str(edge.get("to", ""))
            ]
            if not ext_refs:
                support_pass = False
    
    return {
        "id": qid,
        "query": query,
        "primary_pass": primary_pass,
        "graph_path_pass": graph_path_pass,
        "support_pass": support_pass,
        "latency_ms": latency_ms,
        "primary_hit": {
            "law_key": primary_hit["law_key"],
            "section_num": primary_hit["section_num"],
            "moment": primary_hit["moment"],
            "score": primary_hit["score"],
        },
        "supporting_count": len(supporting),
        "normipolku_count": len(normipolku),
    }


def generate_report(results: list[dict], output_path: Path) -> None:
    """Generate a markdown report from evaluation results."""
    total = len(results)
    primary_pass = sum(1 for r in results if r.get("primary_pass"))
    graph_pass = sum(1 for r in results if r.get("graph_path_pass"))
    support_pass = sum(1 for r in results if r.get("support_pass"))
    avg_latency = sum(r.get("latency_ms", 0) for r in results) / total if total else 0
    
    lines: list[str] = []
    lines.append("# v8 Graph-needed Eval Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Questions | {total} |")
    lines.append(f"| PRIMARY_PASS | {primary_pass}/{total} ({100*primary_pass/total:.1f}%) |")
    lines.append(f"| GRAPH_PATH_PASS | {graph_pass}/{total} ({100*graph_pass/total:.1f}%) |")
    lines.append(f"| SUPPORT_PASS | {support_pass}/{total} ({100*support_pass/total:.1f}%) |")
    lines.append(f"| Avg Latency | {avg_latency:.1f} ms |")
    lines.append("")
    
    # Gate status
    primary_rate = primary_pass / total if total else 0
    graph_rate = graph_pass / total if total else 0
    support_rate = support_pass / total if total else 0
    
    lines.append("## Gate Status")
    lines.append("")
    lines.append(f"- PRIMARY_PASS >= 80%: {'PASS' if primary_rate >= 0.80 else 'FAIL'}")
    lines.append(f"- GRAPH_PATH_PASS >= 70%: {'PASS' if graph_rate >= 0.70 else 'FAIL'}")
    lines.append(f"- SUPPORT_PASS >= 60%: {'PASS' if support_rate >= 0.60 else 'FAIL'}")
    lines.append(f"- Latency < 500 ms: {'PASS' if avg_latency < 500 else 'FAIL'}")
    lines.append("")
    
    # Detailed results
    lines.append("## Detailed Results")
    lines.append("")
    lines.append("| ID | Query | Primary | Graph | Support | Latency |")
    lines.append("|---|---|---|---|---|---|")
    
    for r in results:
        primary = "PASS" if r.get("primary_pass") else "FAIL"
        graph = "PASS" if r.get("graph_path_pass") else "FAIL"
        support = "PASS" if r.get("support_pass") else "FAIL"
        latency = f"{r.get('latency_ms', 0):.0f}ms"
        query_short = r.get("query", "")[:40] + "..." if len(r.get("query", "")) > 40 else r.get("query", "")
        lines.append(f"| {r['id']} | {query_short} | {primary} | {graph} | {support} | {latency} |")
    
    lines.append("")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> None:
    print("=" * 60)
    print("v8: Graph-needed Eval")
    print("=" * 60)
    
    # Load questions
    questions_path = PROJECT_ROOT / "graph" / "eval" / "questions_graph_needed.json"
    if not questions_path.exists():
        print(f"ERROR: {questions_path} not found")
        sys.exit(1)
    
    with open(questions_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    questions = data.get("questions", [])
    print(f"\nLoaded {len(questions)} questions")
    
    # Load indices
    print("\nLoading indices...")
    indices = load_indices()
    print(f"  Loaded: {len(indices)} indices")
    
    # Load model
    print("\nLoading embedding model...")
    model = SentenceTransformer("BAAI/bge-m3")
    
    # Initialize graph builder
    print("\nInitializing graph context builder...")
    graph_builder = GraphContextBuilder()
    
    # Run evaluation
    print("\nRunning evaluation...")
    results: list[dict] = []
    
    for i, q in enumerate(questions):
        result = evaluate_question(q, indices, model, graph_builder)
        results.append(result)
        
        status = "PASS" if result["primary_pass"] else "FAIL"
        print(f"  [{i+1}/{len(questions)}] {q['id']}: {status}")
    
    # Save results
    results_path = PROJECT_ROOT / "graph" / "eval" / "results_graph_needed.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Generate report
    report_path = PROJECT_ROOT / "graph" / "eval" / "report_graph_needed.md"
    generate_report(results, report_path)
    
    # Print summary
    total = len(results)
    primary_pass = sum(1 for r in results if r.get("primary_pass"))
    graph_pass = sum(1 for r in results if r.get("graph_path_pass"))
    support_pass = sum(1 for r in results if r.get("support_pass"))
    avg_latency = sum(r.get("latency_ms", 0) for r in results) / total if total else 0
    
    print("\n" + "=" * 60)
    print("Results Summary")
    print("=" * 60)
    print(f"  PRIMARY_PASS:     {primary_pass}/{total} ({100*primary_pass/total:.1f}%)")
    print(f"  GRAPH_PATH_PASS:  {graph_pass}/{total} ({100*graph_pass/total:.1f}%)")
    print(f"  SUPPORT_PASS:     {support_pass}/{total} ({100*support_pass/total:.1f}%)")
    print(f"  Avg Latency:      {avg_latency:.1f} ms")
    print("=" * 60)
    print(f"\nReport: {report_path}")
    print(f"Results: {results_path}")


if __name__ == "__main__":
    main()

