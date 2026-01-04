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

# v7.1 Rerank configuration
ROUTER_BONUS = 0.02  # Bonus for hits from router's top-weighted law
DIVERSITY_GAP = 0.02  # If score gap between top 2 laws < this, ensure diversity

# v7.1 Pair-guards: (query_term, target_law, bonus/penalty)
# Positive = boost, Negative = penalty
PAIR_GUARDS: list[tuple[str, str, float]] = [
    # "kunnan" in query → boost kuntalaki, penalize kirjanpitolaki
    ("kunnan", "kuntalaki_410_2015", +0.03),
    ("kunnan", "kirjanpitolaki_1336_1997", -0.03),
    ("kunta", "kuntalaki_410_2015", +0.02),
    ("kunta", "kirjanpitolaki_1336_1997", -0.02),
    # "konserni" → boost osakeyhtiölaki
    ("konserni", "osakeyhtiolaki_624_2006", +0.02),
    # "tilintarkastaja" → boost tilintarkastuslaki
    ("tilintarkastaja", "tilintarkastuslaki_1141_2015", +0.02),
    # "hankinta" → boost hankintalaki
    ("hankinta", "hankintalaki_1397_2016", +0.02),
]

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


def load_questions(use_autofill: bool = True) -> list[dict]:
    """Load all cross-law question files.
    
    Args:
        use_autofill: If True, prefer .autofill.json files (v7)
    """
    all_questions: list[dict] = []
    
    if use_autofill:
        # v7: Use autofilled files
        question_files = list(EVAL_HARNESS_DIR.glob("questions_cross_*.autofill.json"))
        if not question_files:
            print("  No autofill files found, falling back to original files")
            question_files = list(EVAL_HARNESS_DIR.glob("questions_cross_*.json"))
            question_files = [f for f in question_files if ".autofill." not in f.name]
    else:
        question_files = list(EVAL_HARNESS_DIR.glob("questions_cross_*.json"))
        question_files = [f for f in question_files if ".autofill." not in f.name]
    
    for qf in question_files:
        with open(qf, encoding="utf-8") as f:
            data = json.load(f)
            questions = data.get("questions", [])
            # Tag each question with its source file
            for q in questions:
                q["source_file"] = qf.name
                # Skip questions that failed autofill
                if q.get("autofill_status") == "FAIL":
                    print(f"  SKIP (autofill FAIL): {q.get('id')}")
                    continue
            # Filter out failed autofill questions
            questions = [q for q in questions if q.get("autofill_status") != "FAIL"]
            all_questions.extend(questions)
            print(f"  Loaded {len(questions)} questions from {qf.name}")
    
    return all_questions


def multi_law_query(
    query: str,
    indices: dict[str, chromadb.Collection],
    model: SentenceTransformer,
    total_k: int = K_TOTAL,
    min_score: float = MIN_SCORE,
    apply_rerank: bool = True,
) -> tuple[list[dict], float, dict]:
    """
    Query multiple law indices and merge results (v7.1: with router bonus + diversity).
    
    Returns:
        Tuple of (results, latency_ms, debug_info)
    """
    start_time = time.perf_counter()
    debug_info: dict = {"router_bonus_applied": 0, "diversity_swap": False, "pair_guards_applied": 0}
    
    # Route query to determine weights
    available_laws = list(indices.keys())
    weights = route_query(query, available_laws)
    
    # Determine top 2 laws from router
    sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
    top1_law = sorted_weights[0][0] if sorted_weights else None
    top2_law = sorted_weights[1][0] if len(sorted_weights) > 1 else None
    debug_info["router_top1"] = top1_law
    debug_info["router_top2"] = top2_law
    debug_info["router_weights"] = weights
    
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
                    "score_original": score,  # Keep original for debugging
                    "section_num": meta.get("section_num", 0),
                    "section_id": meta.get("section_id", ""),
                    "moment": meta.get("moment", ""),
                    "section_title": meta.get("section_title", ""),
                    "node_id": meta.get("node_id", ""),
                })
    
    # v7.1: Apply router bonus (+0.02) to hits from router's top law
    if apply_rerank and top1_law:
        for r in all_results:
            if r["law_key"] == top1_law:
                r["score"] += ROUTER_BONUS
                debug_info["router_bonus_applied"] += 1
    
    # v7.1: Apply pair-guards based on query terms
    if apply_rerank:
        query_lower = query.lower()
        for term, law_key, adjustment in PAIR_GUARDS:
            if term in query_lower:
                for r in all_results:
                    if r["law_key"] == law_key:
                        r["score"] += adjustment
                        debug_info["pair_guards_applied"] += 1
    
    # Sort by score (after bonus)
    all_results.sort(key=lambda x: x["score"], reverse=True)
    
    # v7.1: Diversity rule - ensure at least 1 hit from top2_law if gap is small
    if apply_rerank and top2_law and len(all_results) >= 2:
        # Find best scores per law
        best_scores: dict[str, float] = {}
        for r in all_results:
            law = r["law_key"]
            if law not in best_scores or r["score"] > best_scores[law]:
                best_scores[law] = r["score"]
        
        best1 = best_scores.get(top1_law, 0)
        best2 = best_scores.get(top2_law, 0)
        
        # Check if top2_law is present in top_k
        top_k_results = all_results[:total_k]
        top2_in_topk = any(r["law_key"] == top2_law for r in top_k_results)
        
        # If gap is small and top2_law not in top_k, swap in the best hit from top2_law
        if abs(best1 - best2) < DIVERSITY_GAP and not top2_in_topk:
            # Find best hit from top2_law
            top2_hits = [r for r in all_results if r["law_key"] == top2_law]
            if top2_hits:
                # Replace last item in top_k with best top2_law hit
                top_k_results[-1] = top2_hits[0]
                all_results = top_k_results + [r for r in all_results[total_k:]]
                debug_info["diversity_swap"] = True
    
    latency_ms = (time.perf_counter() - start_time) * 1000
    
    return all_results[:total_k], latency_ms, debug_info


def evaluate_question(
    question: dict,
    results: list[dict],
) -> dict:
    """Evaluate a single question against results (v7: STRICT + ROUTING)."""
    expected_any = question.get("expected_any", [])
    expected_none = question.get("expected_none", [])
    
    # v7 metrics
    pass_strict = False  # law_key + section_num + moment match
    pass_routing = False  # law_key match only
    top1_hit_strict = False
    top1_hit_routing = False
    hard_negative_violation = False
    matched_result = None
    
    for exp in expected_any:
        exp_law_key = exp.get("law_key")
        exp_section_num = exp.get("section_num")
        exp_moment = exp.get("moment")
        
        for i, result in enumerate(results):
            result_law = result["law_key"]
            result_section = int(result.get("section_num", 0))
            result_moment = str(result.get("moment", ""))
            
            # Check law match (ROUTING)
            if result_law == exp_law_key:
                if not pass_routing:
                    pass_routing = True
                    if i == 0:
                        top1_hit_routing = True
                
                # Check strict match (STRICT): law + section + moment
                if result_section == int(exp_section_num):
                    # Check moment if specified
                    if exp_moment is not None:
                        if result_moment == str(exp_moment):
                            pass_strict = True
                            if i == 0:
                                top1_hit_strict = True
                            matched_result = result
                    else:
                        pass_strict = True
                        if i == 0:
                            top1_hit_strict = True
                        matched_result = result
        
        if pass_strict:
            break
    
    # Check for hard negative violations
    if expected_none and results:
        top1_law = results[0].get("law_key", "")
        if top1_law in expected_none:
            hard_negative_violation = True
    
    return {
        "pass_strict": pass_strict,
        "pass_routing": pass_routing,
        "top1_hit_strict": top1_hit_strict,
        "top1_hit_routing": top1_hit_routing,
        "hard_negative_violation": hard_negative_violation,
        "matched_result": matched_result,
        "top1_result": results[0] if results else None,
    }


def run_evaluation(
    questions: list[dict],
    indices: dict[str, chromadb.Collection],
    model: SentenceTransformer,
) -> dict:
    """Run full evaluation and return results (v7.1: with rerank stats)."""
    results: list[dict] = []
    total_latency = 0.0
    total_router_bonus = 0
    total_diversity_swaps = 0
    total_pair_guards = 0
    
    for i, q in enumerate(questions):
        query = q.get("query", "")
        
        # Run query (v7.1: now returns debug_info)
        hits, latency_ms, debug_info = multi_law_query(query, indices, model)
        total_latency += latency_ms
        total_router_bonus += debug_info.get("router_bonus_applied", 0)
        total_pair_guards += debug_info.get("pair_guards_applied", 0)
        if debug_info.get("diversity_swap"):
            total_diversity_swaps += 1
        
        # Evaluate
        eval_result = evaluate_question(q, hits)
        
        results.append({
            "id": q.get("id", f"Q-{i}"),
            "query": query,
            "type": q.get("type", "SHOULD"),
            "test_type": q.get("test_type", "cross_law"),
            "source_file": q.get("source_file", ""),
            "pass_strict": eval_result["pass_strict"],
            "pass_routing": eval_result["pass_routing"],
            "top1_hit_strict": eval_result["top1_hit_strict"],
            "top1_hit_routing": eval_result["top1_hit_routing"],
            "hard_negative_violation": eval_result["hard_negative_violation"],
            "expected_any": q.get("expected_any", []),
            "expected_none": q.get("expected_none", []),
            "matched_result": eval_result["matched_result"],
            "top1_result": eval_result["top1_result"],
            "latency_ms": latency_ms,
        })
        
        # Progress (v7: show both STRICT and ROUTING)
        status_strict = "STRICT" if eval_result["pass_strict"] else "strict-FAIL"
        status_routing = "ROUTE" if eval_result["pass_routing"] else "route-FAIL"
        hn = " [HN-VIOL]" if eval_result["hard_negative_violation"] else ""
        print(f"  [{i+1}/{len(questions)}] {q.get('id', 'Q')}: {status_strict} | {status_routing}{hn}")
    
    # Calculate metrics (v7: STRICT + ROUTING)
    total = len(results)
    pass_strict = sum(1 for r in results if r["pass_strict"])
    pass_routing = sum(1 for r in results if r["pass_routing"])
    top1_strict = sum(1 for r in results if r["top1_hit_strict"])
    top1_routing = sum(1 for r in results if r["top1_hit_routing"])
    hard_neg_violations = sum(1 for r in results if r["hard_negative_violation"])
    avg_latency = total_latency / total if total > 0 else 0.0
    
    # Per-pair metrics
    pair_metrics: dict[str, dict] = {}
    for r in results:
        source = r["source_file"].replace("questions_cross_kunta_", "").replace(".autofill.json", "").replace(".json", "")
        if source not in pair_metrics:
            pair_metrics[source] = {
                "total": 0, 
                "pass_strict": 0, 
                "pass_routing": 0,
                "top1_strict": 0, 
                "top1_routing": 0,
                "hn_viol": 0,
            }
        pair_metrics[source]["total"] += 1
        if r["pass_strict"]:
            pair_metrics[source]["pass_strict"] += 1
        if r["pass_routing"]:
            pair_metrics[source]["pass_routing"] += 1
        if r["top1_hit_strict"]:
            pair_metrics[source]["top1_strict"] += 1
        if r["top1_hit_routing"]:
            pair_metrics[source]["top1_routing"] += 1
        if r["hard_negative_violation"]:
            pair_metrics[source]["hn_viol"] += 1
    
    return {
        "timestamp": datetime.now().isoformat(),
        "version": "7.1",
        "config": {
            "k_total": K_TOTAL,
            "min_score": MIN_SCORE,
            "router_bonus": ROUTER_BONUS,
            "diversity_gap": DIVERSITY_GAP,
        },
        "summary": {
            "total": total,
            # STRICT metrics (gate)
            "pass_strict": pass_strict,
            "pass_rate_strict": pass_strict / total if total > 0 else 0.0,
            "top1_strict": top1_strict,
            "top1_rate_strict": top1_strict / total if total > 0 else 0.0,
            # ROUTING metrics (diagnostic)
            "pass_routing": pass_routing,
            "pass_rate_routing": pass_routing / total if total > 0 else 0.0,
            "top1_routing": top1_routing,
            "top1_rate_routing": top1_routing / total if total > 0 else 0.0,
            # Other
            "hard_negative_violations": hard_neg_violations,
            "avg_latency_ms": avg_latency,
            # v7.1 rerank stats
            "total_router_bonus_applied": total_router_bonus,
            "total_diversity_swaps": total_diversity_swaps,
            "total_pair_guards_applied": total_pair_guards,
        },
        "pair_metrics": pair_metrics,
        "questions": results,
    }


def check_gates(summary: dict) -> dict[str, bool]:
    """Check quality gates (v7: STRICT is the gate)."""
    gates = {
        "pass_rate_strict_95": summary["pass_rate_strict"] >= 0.95,
        "hard_negative_violations_0": summary["hard_negative_violations"] == 0,
        "latency_150ms": summary["avg_latency_ms"] < 150,
    }
    return gates


def generate_report(eval_results: dict) -> str:
    """Generate markdown report (v7.1: STRICT + ROUTING + rerank stats)."""
    summary = eval_results["summary"]
    pair_metrics = eval_results["pair_metrics"]
    gates = check_gates(summary)
    config = eval_results["config"]
    
    lines = [
        "# Cross-Law Evaluation Report (v7.1)",
        "",
        f"**Generated:** {eval_results['timestamp']}",
        f"**Config:** k={config['k_total']}, min_score={config['min_score']}, router_bonus={config.get('router_bonus', 0)}, diversity_gap={config.get('diversity_gap', 0)}",
        "",
        "## Quality Gates (STRICT)",
        "",
        "| Gate | Target | Actual | Status |",
        "|------|--------|--------|--------|",
        f"| Pass Rate STRICT | >= 95% | {summary['pass_rate_strict']*100:.1f}% | {'PASS' if gates['pass_rate_strict_95'] else 'FAIL'} |",
        f"| Hard Negatives | = 0 | {summary['hard_negative_violations']} | {'PASS' if gates['hard_negative_violations_0'] else 'FAIL'} |",
        f"| Latency | < 150ms | {summary['avg_latency_ms']:.1f}ms | {'PASS' if gates['latency_150ms'] else 'FAIL'} |",
        "",
        f"**Overall Gate Status:** {'PASS' if all(gates.values()) else 'FAIL'}",
        "",
        "## Summary",
        "",
        "### STRICT (law_key + section_num + moment match) - **GATE**",
        f"- **Passed:** {summary['pass_strict']}/{summary['total']} ({summary['pass_rate_strict']*100:.1f}%)",
        f"- **Top-1 Hits:** {summary['top1_strict']} ({summary['top1_rate_strict']*100:.1f}%)",
        "",
        "### ROUTING (law_key match only) - *diagnostic*",
        f"- **Passed:** {summary['pass_routing']}/{summary['total']} ({summary['pass_rate_routing']*100:.1f}%)",
        f"- **Top-1 Hits:** {summary['top1_routing']} ({summary['top1_rate_routing']*100:.1f}%)",
        "",
        "### Other",
        f"- **Hard Negative Violations:** {summary['hard_negative_violations']}",
        f"- **Avg Latency:** {summary['avg_latency_ms']:.1f}ms",
        "",
        "### v7.1 Rerank Stats",
        f"- **Router Bonus Applied:** {summary.get('total_router_bonus_applied', 0)} times",
        f"- **Pair Guards Applied:** {summary.get('total_pair_guards_applied', 0)} times",
        f"- **Diversity Swaps:** {summary.get('total_diversity_swaps', 0)} times",
        "",
        "## Per-Pair Metrics",
        "",
        "| Pair | Total | STRICT | STRICT% | ROUTING% | Top1-S | HN |",
        "|------|-------|--------|---------|----------|--------|-----|",
    ]
    
    for pair, metrics in sorted(pair_metrics.items()):
        strict_pct = (metrics["pass_strict"] / metrics["total"] * 100) if metrics["total"] > 0 else 0
        routing_pct = (metrics["pass_routing"] / metrics["total"] * 100) if metrics["total"] > 0 else 0
        top1_pct = (metrics["top1_strict"] / metrics["total"] * 100) if metrics["total"] > 0 else 0
        lines.append(f"| {pair.upper()} | {metrics['total']} | {metrics['pass_strict']} | {strict_pct:.1f}% | {routing_pct:.1f}% | {top1_pct:.1f}% | {metrics['hn_viol']} |")
    
    # Failed questions (STRICT)
    failed = [q for q in eval_results["questions"] if not q["pass_strict"]]
    if failed:
        lines.extend([
            "",
            "## Failed Questions (STRICT)",
            "",
        ])
        for q in failed[:20]:  # Limit to first 20 to keep report manageable
            top1 = q.get("top1_result") or {}
            if top1:
                top1_info = f"{top1.get('law_key', 'N/A')} §{top1.get('section_num', 'N/A')}.{top1.get('moment', '?')}"
                score_info = f" (score: {top1.get('score', 0):.4f})"
                routing_ok = "ROUTE-OK" if q.get("pass_routing") else "route-fail"
            else:
                top1_info = "No results"
                score_info = ""
                routing_ok = "route-fail"
            lines.append(f"- **{q['id']}** [{routing_ok}]: {q['query'][:50]}...")
            lines.append(f"  - Expected: {q['expected_any']}")
            lines.append(f"  - Top-1: {top1_info}{score_info}")
        
        if len(failed) > 20:
            lines.append(f"\n*...and {len(failed) - 20} more failed questions*")
    
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
    """Run cross-law evaluation (v7.1: with router bonus + diversity)."""
    print("=" * 60)
    print("Cross-Law Evaluation (v7.1)")
    print(f"  Router Bonus: +{ROUTER_BONUS}")
    print(f"  Diversity Gap: {DIVERSITY_GAP}")
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
    
    # Print summary (v7.1)
    summary = eval_results["summary"]
    print("\n" + "=" * 60)
    print("SUMMARY (v7.1)")
    print("=" * 60)
    print("\nSTRICT (gate):")
    print(f"  Pass Rate: {summary['pass_rate_strict']*100:.1f}%")
    print(f"  Top-1 Hit Rate: {summary['top1_rate_strict']*100:.1f}%")
    print("\nROUTING (diagnostic):")
    print(f"  Pass Rate: {summary['pass_rate_routing']*100:.1f}%")
    print(f"  Top-1 Hit Rate: {summary['top1_rate_routing']*100:.1f}%")
    print(f"\nHard Negative Violations: {summary['hard_negative_violations']}")
    print(f"Avg Latency: {summary['avg_latency_ms']:.1f}ms")
    print(f"\nv7.1 Rerank Stats:")
    print(f"  Router Bonus Applied: {summary.get('total_router_bonus_applied', 0)} times")
    print(f"  Pair Guards Applied: {summary.get('total_pair_guards_applied', 0)} times")
    print(f"  Diversity Swaps: {summary.get('total_diversity_swaps', 0)} times")
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
        # Don't exit with error for now - we're in development
        # sys.exit(1)


if __name__ == "__main__":
    main()

