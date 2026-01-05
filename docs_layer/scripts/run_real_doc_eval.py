#!/usr/bin/env python3
"""
v9.3: Real-doc Eval Runner

Evaluates the combined Law↔Document retrieval system.
Tests both legal retrieval accuracy AND document evidence finding.

Usage:
    python docs_layer/scripts/run_real_doc_eval.py --questions <questions.json> --doc-index <chroma_dir> --output <output_dir>
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Install: pip install chromadb sentence-transformers")
    exit(1)


# Law index configuration (same as scripts/run_graph_eval.py)
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
}

# Query parameters
K_LAW = 5
K_DOC = 5
MIN_SCORE = 0.40


def load_questions(questions_path: Path) -> list[dict]:
    """Load evaluation questions."""
    with open(questions_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("questions", [])


def load_law_indices(model: SentenceTransformer) -> dict:
    """Load law ChromaDB indices."""
    indices = {}
    for law_key, config in LAW_INDICES.items():
        chroma_path = config["chroma_path"]
        if chroma_path.exists():
            client = chromadb.PersistentClient(path=str(chroma_path))
            try:
                collection = client.get_collection(config["collection_name"])
                indices[law_key] = {"client": client, "collection": collection}
            except Exception as e:
                print(f"  Warning: Could not load {law_key}: {e}")
    return indices


def load_doc_index(doc_index_path: Path, collection_name: str = "lapua_2023"):
    """Load document ChromaDB index."""
    client = chromadb.PersistentClient(path=str(doc_index_path))
    collection = client.get_collection(collection_name)
    return {"client": client, "collection": collection}


def query_law_index(
    query: str,
    expected_law_key: str,
    indices: dict,
    model: SentenceTransformer,
    k: int = K_LAW,
) -> list[dict]:
    """Query specific law index."""
    if expected_law_key not in indices:
        return []
    
    collection = indices[expected_law_key]["collection"]
    embedding = model.encode([query], normalize_embeddings=True)[0].tolist()
    
    results = collection.query(
        query_embeddings=[embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    
    hits = []
    for i, doc_id in enumerate(results["ids"][0]):
        distance = results["distances"][0][i]
        score = 1 - distance
        
        if score < MIN_SCORE:
            continue
        
        meta = results["metadatas"][0][i]
        hits.append({
            "node_id": meta.get("node_id", doc_id),
            "law_key": expected_law_key,
            "section_num": meta.get("section_num"),
            "moment": meta.get("moment"),
            "score": score,
            "text": results["documents"][0][i][:200],
        })
    
    return hits


def query_doc_index(
    query: str,
    doc_index: dict,
    model: SentenceTransformer,
    k: int = K_DOC,
) -> list[dict]:
    """Query document index."""
    collection = doc_index["collection"]
    embedding = model.encode([query], normalize_embeddings=True)[0].tolist()
    
    results = collection.query(
        query_embeddings=[embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    
    hits = []
    for i, doc_id in enumerate(results["ids"][0]):
        distance = results["distances"][0][i]
        score = 1 - distance
        
        meta = results["metadatas"][0][i]
        hits.append({
            "doc_node_id": doc_id,
            "node_type": meta.get("node_type"),
            "title": meta.get("title", ""),
            "page_num": meta.get("page_num"),
            "score": score,
            "text": results["documents"][0][i][:200],
        })
    
    return hits


def check_law_pass(law_hits: list[dict], expected_law: dict) -> bool:
    """Check if law retrieval passed."""
    if not law_hits:
        return False
    
    expected_section = expected_law.get("section_num")
    expected_moment = expected_law.get("moment")
    
    for hit in law_hits:
        # Section match
        if expected_section is not None:
            if hit.get("section_num") != expected_section:
                continue
        
        # Moment match (optional)
        if expected_moment is not None:
            if str(hit.get("moment")) != str(expected_moment):
                continue
        
        return True
    
    return False


def check_doc_pass(doc_hits: list[dict], expected_doc: dict) -> bool:
    """Check if document retrieval passed."""
    if not doc_hits:
        return False
    
    passed = False
    
    # Check section pattern
    section_pattern = expected_doc.get("section_pattern")
    if section_pattern:
        pattern = re.compile(section_pattern, re.IGNORECASE)
        for hit in doc_hits:
            title = hit.get("title", "")
            node_id = hit.get("doc_node_id", "")
            text = hit.get("text", "")
            if pattern.search(title) or pattern.search(node_id) or pattern.search(text):
                passed = True
                break
    
    # Check node type
    expected_type = expected_doc.get("node_type")
    if expected_type and not passed:
        for hit in doc_hits:
            if hit.get("node_type") == expected_type:
                passed = True
                break
    
    # Check metric name (also check in text/title)
    metric_name = expected_doc.get("metric_name")
    if metric_name and not passed:
        for hit in doc_hits:
            node_id = hit.get("doc_node_id", "")
            title = hit.get("title", "").lower()
            text = hit.get("text", "").lower()
            if metric_name in node_id or metric_name in title or metric_name.replace("_", " ") in text:
                passed = True
                break
    
    # Check page range
    page_range = expected_doc.get("page_range")
    if page_range and not passed:
        for hit in doc_hits:
            page = hit.get("page_num", 0)
            if page and page_range[0] <= page <= page_range[1]:
                passed = True
                break
    
    # Fallback: if no specific checks, pass if any hit exists
    if not (section_pattern or expected_type or metric_name or page_range):
        passed = len(doc_hits) > 0
    
    return passed


def check_evidence_pass(doc_hits: list[dict], anchor_terms: list[str]) -> bool:
    """Check if evidence contains anchor terms."""
    if not anchor_terms or not doc_hits:
        return True  # No anchor terms to check
    
    all_text = " ".join(hit.get("text", "") + " " + hit.get("title", "") for hit in doc_hits)
    all_text_lower = all_text.lower()
    
    # At least one anchor term should be found
    for term in anchor_terms:
        if term.lower() in all_text_lower:
            return True
    
    return False


def evaluate_question(
    question: dict,
    law_indices: dict,
    doc_index: dict,
    model: SentenceTransformer,
) -> dict:
    """Evaluate a single question."""
    query = question["query"]
    expected_law = question.get("expected_law", {})
    expected_doc = question.get("expected_doc", {})
    anchor_terms = question.get("anchor_terms", [])
    
    start_time = time.time()
    
    # Query law index
    law_key = expected_law.get("law_key", "")
    law_hits = query_law_index(query, law_key, law_indices, model)
    
    # Query document index
    doc_hits = query_doc_index(query, doc_index, model)
    
    latency_ms = (time.time() - start_time) * 1000
    
    # Evaluate passes
    law_pass = check_law_pass(law_hits, expected_law)
    doc_pass = check_doc_pass(doc_hits, expected_doc)
    evidence_pass = check_evidence_pass(doc_hits, anchor_terms)
    
    return {
        "id": question["id"],
        "query": query,
        "law_pass": law_pass,
        "doc_pass": doc_pass,
        "evidence_pass": evidence_pass,
        "latency_ms": latency_ms,
        "law_top1": law_hits[0] if law_hits else None,
        "doc_top1": doc_hits[0] if doc_hits else None,
    }


def generate_report(results: list[dict], output_path: Path) -> None:
    """Generate Markdown report."""
    total = len(results)
    law_passed = sum(1 for r in results if r["law_pass"])
    doc_passed = sum(1 for r in results if r["doc_pass"])
    evidence_passed = sum(1 for r in results if r["evidence_pass"])
    avg_latency = sum(r["latency_ms"] for r in results) / total if total else 0
    
    # Gates
    law_rate = law_passed / total * 100 if total else 0
    doc_rate = doc_passed / total * 100 if total else 0
    evidence_rate = evidence_passed / total * 100 if total else 0
    
    law_gate = "PASS" if law_rate >= 95 else "FAIL"
    doc_gate = "PASS" if doc_rate >= 85 else "FAIL"
    evidence_gate = "PASS" if evidence_rate >= 85 else "FAIL"
    latency_gate = "PASS" if avg_latency < 250 else "FAIL"
    
    overall = "PASS" if all(g == "PASS" for g in [law_gate, doc_gate, evidence_gate, latency_gate]) else "FAIL"
    
    lines = [
        "# v9 Real-doc Eval Report",
        "",
        "## Summary",
        "",
        "| Gate | Value | Target | Status |",
        "|------|-------|--------|--------|",
        f"| **LAW_PASS** | {law_rate:.1f}% | >= 95% | {law_gate} |",
        f"| **DOC_PASS** | {doc_rate:.1f}% | >= 85% | {doc_gate} |",
        f"| **EVIDENCE_PASS** | {evidence_rate:.1f}% | >= 85% | {evidence_gate} |",
        f"| **Latency** | {avg_latency:.1f}ms | < 250ms | {latency_gate} |",
        "",
        f"**OVERALL: {overall}**",
        "",
        "## Detailed Results",
        "",
        "| ID | Query | LAW | DOC | EVIDENCE | Latency |",
        "|----|-------|-----|-----|----------|---------|",
    ]
    
    for r in results:
        law_icon = "Pass" if r["law_pass"] else "FAIL"
        doc_icon = "Pass" if r["doc_pass"] else "FAIL"
        ev_icon = "Pass" if r["evidence_pass"] else "FAIL"
        query_short = r["query"][:40] + "..." if len(r["query"]) > 40 else r["query"]
        lines.append(f"| {r['id']} | {query_short} | {law_icon} | {doc_icon} | {ev_icon} | {r['latency_ms']:.0f}ms |")
    
    # Failures
    failures = [r for r in results if not (r["law_pass"] and r["doc_pass"])]
    if failures:
        lines.extend([
            "",
            "## Failures",
            "",
        ])
        for r in failures:
            lines.append(f"### {r['id']}")
            lines.append(f"- Query: {r['query']}")
            lines.append(f"- LAW_PASS: {r['law_pass']}")
            lines.append(f"- DOC_PASS: {r['doc_pass']}")
            if r["law_top1"]:
                lines.append(f"- Law Top-1: {r['law_top1'].get('node_id', 'N/A')}")
            if r["doc_top1"]:
                lines.append(f"- Doc Top-1: {r['doc_top1'].get('doc_node_id', 'N/A')}")
            lines.append("")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"Report: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="v9 Real-doc Eval")
    parser.add_argument("--questions", "-q", required=True, help="Path to questions JSON")
    parser.add_argument("--doc-index", "-d", required=True, help="Path to document ChromaDB")
    parser.add_argument("--output", "-o", required=True, help="Output directory")
    args = parser.parse_args()
    
    questions_path = Path(args.questions)
    doc_index_path = Path(args.doc_index)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("v9: Real-doc Eval")
    print("=" * 60)
    
    questions = load_questions(questions_path)
    print(f"\nLoaded {len(questions)} questions")
    
    print("\nLoading embedding model...")
    model = SentenceTransformer("BAAI/bge-m3")
    
    print("\nLoading law indices...")
    law_indices = load_law_indices(model)
    print(f"  Loaded: {len(law_indices)} law indices")
    
    print("\nLoading document index...")
    doc_index = load_doc_index(doc_index_path)
    
    print("\nRunning evaluation...")
    results = []
    for i, q in enumerate(questions):
        result = evaluate_question(q, law_indices, doc_index, model)
        status = "PASS" if result["law_pass"] and result["doc_pass"] else "FAIL"
        print(f"  [{i+1}/{len(questions)}] {q['id']}: {status}")
        results.append(result)
    
    # Calculate summary
    total = len(results)
    law_passed = sum(1 for r in results if r["law_pass"])
    doc_passed = sum(1 for r in results if r["doc_pass"])
    evidence_passed = sum(1 for r in results if r["evidence_pass"])
    avg_latency = sum(r["latency_ms"] for r in results) / total if total else 0
    
    print("\n" + "=" * 60)
    print("Results Summary")
    print("=" * 60)
    print(f"  LAW_PASS:      {law_passed}/{total} ({law_passed/total*100:.1f}%)")
    print(f"  DOC_PASS:      {doc_passed}/{total} ({doc_passed/total*100:.1f}%)")
    print(f"  EVIDENCE_PASS: {evidence_passed}/{total} ({evidence_passed/total*100:.1f}%)")
    print(f"  Avg Latency:   {avg_latency:.1f} ms")
    print("=" * 60)
    
    # Write results
    results_path = output_dir / "results_real_doc.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults: {results_path}")
    
    # Generate report
    report_path = output_dir / "report_real_doc.md"
    generate_report(results, report_path)


if __name__ == "__main__":
    main()

