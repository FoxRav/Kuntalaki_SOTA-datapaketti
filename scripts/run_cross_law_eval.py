"""
Cross-law evaluation script (v6).

Evaluates multi-law retrieval accuracy across different law pairs.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"Missing dependency: {e}")
    sys.exit(1)

from shared.query_rules.law_router import route_query, calculate_k_per_law


# Configuration
K_TOTAL = 10
MIN_SCORE = 0.50
EVAL_HARNESS_DIR = PROJECT_ROOT / "shared" / "eval_harness"

# Law index configurations
LAW_INDICES = {
    "kuntalaki_410_2015": {
        "chroma_path": PROJECT_ROOT / "analysis_layer" / "embeddings" / "chroma_db",
        "collection_name": "kuntalaki",
    },
    "kirjanpitolaki_1336_1997": {
        "chroma_path": PROJECT_ROOT / "laws" / "kirjanpitolaki_1336_1997" / "analysis_layer" / "embeddings" / "chroma_db",
        "collection_name": "kirjanpitolaki",
    },
    "kirjanpitoasetus_1339_1997": {
        "chroma_path": PROJECT_ROOT / "laws" / "kirjanpitoasetus_1339_1997" / "analysis_layer" / "embeddings" / "chroma_db",
        "collection_name": "kirjanpitoasetus",
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
}


def load_indices() -> dict[str, chromadb.Collection]:
    """Load all available law indices."""
    indices: dict[str, chromadb.Collection] = {}
    
    for law_key, config in LAW_INDICES.items():
        chroma_path = config["chroma_path"]
        if chroma_path.exists():
            try:
                client = chromadb.PersistentClient(path=str(chroma_path))
                collection = client.get_collection(config["collection_name"])
                indices[law_key] = collection
                print(f"  Loaded: {law_key} ({collection.count()} docs)")
            except Exception as e:
                print(f"  Warning: Could not load {law_key}: {e}")
    
    return indices


def load_questions() -> list[dict]:
    """Load all cross-law question files."""
    all_questions: list[dict] = []
    
    question_files = list(EVAL_HARNESS_DIR.glob("questions_cross_*.json"))
    
    for qf in question_files:
        with open(qf, encoding="utf-8") as f:
            data = json.load(f)
            questions = data.get("questions", [])
            # Tag each question with its source file
            for q in questions:
                q["source_file"] = qf.name
            all_questions.extend(questions)
            print(f"  Loaded {len(questions)} questions from {qf.name}")
    
    return all_questions


def multi_law_query(
    query: str,
    indices: dict[str, chromadb.Collection],
    model: SentenceTransformer,
    total_k: int = K_TOTAL,
    min_score: float = MIN_SCORE,
) -> tuple[list[dict], float]:
    """
    Query multiple law indices and merge results.
    Returns tuple of (results, latency_ms).
    """
    start_time = time.perf_counter()
    
    # Route query to determine weights
    available_laws = list(indices.keys())
    weights = route_query(query, available_laws)
    
    # Calculate k per law
    k_per_law = calculate_k_per_law(weights, total_k, min_k=2)
    
    # Generate embedding
    embedding = model.encode([query], normalize_embeddings=True)[0].tolist()
    
    # Query each law index
    all_results: list[dict] = []
    
    for law_key, k in k_per_law.items():
        if law_key not in indices:
            continue
            
        collection = indices[law_key]
        results = collection.query(
            query_embeddings=[embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        
        # Convert to result dicts
        for i, (doc, meta, dist) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )):
            score = 1 - dist  # Convert distance to score
            if score >= min_score:
                all_results.append({
                    "law_key": law_key,
                    "score": score,
                    "section_num": meta.get("section_num", 0),
                    "section_id": meta.get("section_id", ""),
                    "moment": meta.get("moment", ""),
                    "section_title": meta.get("section_title", ""),
                    "node_id": meta.get("node_id", ""),
                })
    
    # Sort by score
    all_results.sort(key=lambda x: x["score"], reverse=True)
    
    latency_ms = (time.perf_counter() - start_time) * 1000
    
    return all_results[:total_k], latency_ms


def evaluate_question(
    question: dict,
    results: list[dict],
) -> dict:
    """Evaluate a single question against results."""
    expected_any = question.get("expected_any", [])
    expected_none = question.get("expected_none", [])
    test_type = question.get("test_type", "cross_law")
    
    passed = False
    top1_hit = False
    law_match = False  # Did we find the right law?
    hard_negative_violation = False
    matched_result = None
    
    # For cross_law tests: check if correct LAW is in top-k (section is secondary)
    # For hard_negative tests: check exact section match
    
    for exp in expected_any:
        exp_law_key = exp.get("law_key")
        exp_section_num = exp.get("section_num")
        exp_moment = exp.get("moment")
        
        for i, result in enumerate(results):
            result_law = result["law_key"]
            result_section = int(result.get("section_num", 0))
            result_moment = str(result.get("moment", ""))
            
            # Check law match
            if result_law == exp_law_key:
                law_match = True
                
                # For cross_law tests: law match is enough for pass
                if test_type == "cross_law":
                    passed = True
                    if i == 0:
                        top1_hit = True
                    matched_result = result
                    break
                
                # For hard_negative tests: require exact section match
                elif test_type == "hard_negative":
                    if result_section == int(exp_section_num):
                        # Check moment if specified
                        if exp_moment is not None:
                            if result_moment == str(exp_moment):
                                passed = True
                                if i == 0:
                                    top1_hit = True
                                matched_result = result
                                break
                        else:
                            passed = True
                            if i == 0:
                                top1_hit = True
                            matched_result = result
                            break
        
        if passed:
            break
    
    # Check for hard negative violations
    if expected_none and results:
        top1_law = results[0].get("law_key", "")
        if top1_law in expected_none:
            hard_negative_violation = True
    
    return {
        "passed": passed,
        "top1_hit": top1_hit,
        "law_match": law_match,
        "hard_negative_violation": hard_negative_violation,
        "matched_result": matched_result,
        "top1_result": results[0] if results else None,
    }


def run_evaluation(
    questions: list[dict],
    indices: dict[str, chromadb.Collection],
    model: SentenceTransformer,
) -> dict:
    """Run full evaluation and return results."""
    results: list[dict] = []
    total_latency = 0.0
    
    for i, q in enumerate(questions):
        query = q.get("query", "")
        
        # Run query
        hits, latency_ms = multi_law_query(query, indices, model)
        total_latency += latency_ms
        
        # Evaluate
        eval_result = evaluate_question(q, hits)
        
        results.append({
            "id": q.get("id", f"Q-{i}"),
            "query": query,
            "type": q.get("type", "SHOULD"),
            "test_type": q.get("test_type", "cross_law"),
            "source_file": q.get("source_file", ""),
            "passed": eval_result["passed"],
            "top1_hit": eval_result["top1_hit"],
            "law_match": eval_result.get("law_match", False),
            "hard_negative_violation": eval_result["hard_negative_violation"],
            "expected_any": q.get("expected_any", []),
            "expected_none": q.get("expected_none", []),
            "matched_result": eval_result["matched_result"],
            "top1_result": eval_result["top1_result"],
            "latency_ms": latency_ms,
        })
        
        # Progress
        status = "PASS" if eval_result["passed"] else "FAIL"
        hn = " [HN-VIOL]" if eval_result["hard_negative_violation"] else ""
        print(f"  [{i+1}/{len(questions)}] {q.get('id', 'Q')}: {status}{hn}")
    
    # Calculate metrics
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    top1_hits = sum(1 for r in results if r["top1_hit"])
    hard_neg_violations = sum(1 for r in results if r["hard_negative_violation"])
    avg_latency = total_latency / total if total > 0 else 0.0
    
    # Per-pair metrics
    pair_metrics: dict[str, dict] = {}
    for r in results:
        source = r["source_file"].replace("questions_cross_kunta_", "").replace(".json", "")
        if source not in pair_metrics:
            pair_metrics[source] = {"total": 0, "passed": 0, "top1": 0, "hn_viol": 0}
        pair_metrics[source]["total"] += 1
        if r["passed"]:
            pair_metrics[source]["passed"] += 1
        if r["top1_hit"]:
            pair_metrics[source]["top1"] += 1
        if r["hard_negative_violation"]:
            pair_metrics[source]["hn_viol"] += 1
    
    return {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "k_total": K_TOTAL,
            "min_score": MIN_SCORE,
        },
        "summary": {
            "total": total,
            "passed": passed,
            "pass_rate": passed / total if total > 0 else 0.0,
            "top1_hits": top1_hits,
            "top1_hit_rate": top1_hits / total if total > 0 else 0.0,
            "hard_negative_violations": hard_neg_violations,
            "avg_latency_ms": avg_latency,
        },
        "pair_metrics": pair_metrics,
        "questions": results,
    }


def check_gates(summary: dict) -> dict[str, bool]:
    """Check quality gates."""
    gates = {
        "cross_law_pass_rate_95": summary["pass_rate"] >= 0.95,
        "hard_negative_violations_0": summary["hard_negative_violations"] == 0,
        "latency_150ms": summary["avg_latency_ms"] < 150,
    }
    return gates


def generate_report(eval_results: dict) -> str:
    """Generate markdown report."""
    summary = eval_results["summary"]
    pair_metrics = eval_results["pair_metrics"]
    gates = check_gates(summary)
    
    lines = [
        "# Cross-Law Evaluation Report (v6)",
        "",
        f"**Generated:** {eval_results['timestamp']}",
        f"**Config:** k={eval_results['config']['k_total']}, min_score={eval_results['config']['min_score']}",
        "",
        "## Quality Gates",
        "",
        "| Gate | Target | Actual | Status |",
        "|------|--------|--------|--------|",
        f"| Pass Rate | >= 95% | {summary['pass_rate']*100:.1f}% | {'PASS' if gates['cross_law_pass_rate_95'] else 'FAIL'} |",
        f"| Hard Negatives | = 0 | {summary['hard_negative_violations']} | {'PASS' if gates['hard_negative_violations_0'] else 'FAIL'} |",
        f"| Latency | < 150ms | {summary['avg_latency_ms']:.1f}ms | {'PASS' if gates['latency_150ms'] else 'FAIL'} |",
        "",
        f"**Overall Gate Status:** {'PASS' if all(gates.values()) else 'FAIL'}",
        "",
        "## Summary",
        "",
        f"- **Total Questions:** {summary['total']}",
        f"- **Passed:** {summary['passed']} ({summary['pass_rate']*100:.1f}%)",
        f"- **Top-1 Hits:** {summary['top1_hits']} ({summary['top1_hit_rate']*100:.1f}%)",
        f"- **Hard Negative Violations:** {summary['hard_negative_violations']}",
        f"- **Avg Latency:** {summary['avg_latency_ms']:.1f}ms",
        "",
        "## Per-Pair Metrics",
        "",
        "| Pair | Total | Passed | Pass% | Top-1% | HN-Viol |",
        "|------|-------|--------|-------|--------|---------|",
    ]
    
    for pair, metrics in sorted(pair_metrics.items()):
        pass_pct = (metrics["passed"] / metrics["total"] * 100) if metrics["total"] > 0 else 0
        top1_pct = (metrics["top1"] / metrics["total"] * 100) if metrics["total"] > 0 else 0
        lines.append(f"| {pair.upper()} | {metrics['total']} | {metrics['passed']} | {pass_pct:.1f}% | {top1_pct:.1f}% | {metrics['hn_viol']} |")
    
    # Failed questions
    failed = [q for q in eval_results["questions"] if not q["passed"]]
    if failed:
        lines.extend([
            "",
            "## Failed Questions",
            "",
        ])
        for q in failed:
            top1 = q.get("top1_result") or {}
            if top1:
                top1_info = f"{top1.get('law_key', 'N/A')} §{top1.get('section_num', 'N/A')}"
                score_info = f" (score: {top1.get('score', 0):.4f})"
            else:
                top1_info = "No results"
                score_info = ""
            lines.append(f"- **{q['id']}**: {q['query'][:60]}...")
            lines.append(f"  - Expected: {q['expected_any']}")
            lines.append(f"  - Top-1: {top1_info}{score_info}")
    
    # Hard negative violations
    hn_violations = [q for q in eval_results["questions"] if q["hard_negative_violation"]]
    if hn_violations:
        lines.extend([
            "",
            "## Hard Negative Violations",
            "",
        ])
        for q in hn_violations:
            top1 = q.get("top1_result", {})
            lines.append(f"- **{q['id']}**: {q['query'][:60]}...")
            lines.append(f"  - Expected NOT: {q['expected_none']}")
            lines.append(f"  - Got Top-1: {top1.get('law_key', 'N/A')} (VIOLATION)")
    
    return "\n".join(lines)


def main() -> None:
    """Run cross-law evaluation."""
    print("=" * 60)
    print("Cross-Law Evaluation (v6)")
    print("=" * 60)
    
    # Load indices
    print("\nLoading indices...")
    indices = load_indices()
    
    if not indices:
        print("ERROR: No indices available!")
        sys.exit(1)
    
    # Load questions
    print("\nLoading questions...")
    questions = load_questions()
    print(f"  Total: {len(questions)} questions")
    
    # Load model
    print("\nLoading embedding model...")
    model = SentenceTransformer("BAAI/bge-m3")
    
    # Run evaluation
    print("\nRunning evaluation...")
    eval_results = run_evaluation(questions, indices, model)
    
    # Check gates
    gates = check_gates(eval_results["summary"])
    
    # Save results
    results_path = EVAL_HARNESS_DIR / "results_cross_law.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(eval_results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nResults saved to: {results_path}")
    
    # Generate and save report
    report = generate_report(eval_results)
    report_path = EVAL_HARNESS_DIR / "report_cross_law.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Report saved to: {report_path}")
    
    # Print summary
    summary = eval_results["summary"]
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Pass Rate: {summary['pass_rate']*100:.1f}%")
    print(f"Top-1 Hit Rate: {summary['top1_hit_rate']*100:.1f}%")
    print(f"Hard Negative Violations: {summary['hard_negative_violations']}")
    print(f"Avg Latency: {summary['avg_latency_ms']:.1f}ms")
    print()
    print("GATES:")
    for gate_name, gate_pass in gates.items():
        status = "PASS" if gate_pass else "FAIL"
        print(f"  {gate_name}: {status}")
    print()
    
    overall_pass = all(gates.values())
    if overall_pass:
        print("OVERALL: PASS")
    else:
        print("OVERALL: FAIL")
        sys.exit(1)


if __name__ == "__main__":
    main()

