"""
Kuntalaki retrieval evaluation runner.

Ajaa golden-set kysymykset ja tuottaa laaturaportit.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from statistics import mean, median

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sentence_transformers import SentenceTransformer

from analysis_layer.vector_store.chroma_store import ChromaVectorStore


def query_kuntalaki(
    model: SentenceTransformer,
    store: ChromaVectorStore,
    query: str,
    k: int = 5,
) -> list[dict]:
    """Query the Kuntalaki index and return results.

    Returns list of dicts with: section_num, moment, section_title, node_id, score, text
    """
    embedding = model.encode([query], normalize_embeddings=True)[0]
    results = store.query(embedding.tolist(), n_results=k)

    hits = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        # Parse tags if needed
        tags = meta.get("tags", [])
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except Exception:
                tags = []

        hits.append({
            "section_num": meta.get("section_id", ""),
            "moment": meta.get("moment", ""),
            "section_title": meta.get("section_title", ""),
            "node_id": meta.get("node_id", ""),
            "score": round(1 - dist, 4),  # Convert distance to similarity
            "text": doc[:300],
        })

    return hits


def hit_matches_expected(hit: dict, expected: dict) -> bool:
    """Check if a hit matches an expected result."""
    # Normalize section: "110a" vs "110 a" vs "110"
    sec = str(hit.get("section_num", "")).replace(" ", "").lower()
    mom = str(hit.get("moment", "")).strip()

    exp_sec = str(expected.get("section", "")).replace(" ", "").lower()
    exp_mom = str(expected.get("moment", "")).strip()

    # Section must match; moment is optional (empty means any)
    return sec == exp_sec and (exp_mom == "" or mom == exp_mom)


def eval_one(
    q: dict,
    model: SentenceTransformer,
    store: ChromaVectorStore,
) -> dict:
    """Evaluate a single question."""
    k = int(q.get("k", 5))
    min_score = float(q.get("min_score", 0.55))

    t0 = time.time()
    hits = query_kuntalaki(model, store, q["query"], k=k)
    dt = time.time() - t0

    # Find first matching hit
    first_rank = None
    passed = False

    for i, h in enumerate(hits, start=1):
        if float(h.get("score", 0.0)) < min_score:
            continue
        for exp in q["expected_any"]:
            if hit_matches_expected(h, exp):
                passed = True
                first_rank = i
                break
        if passed:
            break

    # Reciprocal rank for MRR
    rr = 0.0 if first_rank is None else 1.0 / first_rank

    return {
        "id": q["id"],
        "category": q.get("category"),
        "must": bool(q.get("must", False)),
        "query": q["query"],
        "expected_any": q["expected_any"],
        "k": k,
        "min_score": min_score,
        "passed": passed,
        "first_rank": first_rank,
        "rr": rr,
        "latency_ms": round(dt * 1000, 2),
        "hits": hits,
    }


def main() -> None:
    """Run evaluation."""
    root = Path(__file__).parent.parent
    qpath = root / "eval" / "questions_kuntalaki_golden.json"
    out_json = root / "eval" / "kuntalaki_eval_results.json"
    out_md = root / "eval" / "report_kuntalaki_eval.md"

    if not qpath.exists():
        print(f"ERROR: Questions file not found: {qpath}")
        sys.exit(1)

    # Load questions
    questions = json.loads(qpath.read_text(encoding="utf-8"))
    print(f"Loaded {len(questions)} questions")

    # Initialize search
    print("Loading model...")
    model = SentenceTransformer("BAAI/bge-m3")

    chroma_path = root / "analysis_layer" / "embeddings" / "chroma_db"
    if not chroma_path.exists():
        print(f"ERROR: ChromaDB not found: {chroma_path}")
        sys.exit(1)

    store = ChromaVectorStore(chroma_path, "kuntalaki")
    print(f"Connected to index. Documents: {store.count()}")

    # Run evaluation
    print("\nRunning evaluation...")
    results = []
    for i, q in enumerate(questions, 1):
        result = eval_one(q, model, store)
        results.append(result)
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  [{i}/{len(questions)}] {q['id']}: {status}")

    # Calculate metrics
    total = len(results)
    passed_total = sum(1 for r in results if r["passed"])

    must = [r for r in results if r["must"]]
    should = [r for r in results if not r["must"]]

    def rate(xs: list) -> float:
        return 0.0 if not xs else sum(1 for r in xs if r["passed"]) / len(xs)

    mrr = mean([r["rr"] for r in results]) if results else 0.0

    # Score stats (top1)
    top1_scores = []
    for r in results:
        if r["hits"]:
            top1_scores.append(float(r["hits"][0].get("score", 0.0)))

    avg_top1 = mean(top1_scores) if top1_scores else 0.0
    med_top1 = median(top1_scores) if top1_scores else 0.0
    min_top1 = min(top1_scores) if top1_scores else 0.0
    max_top1 = max(top1_scores) if top1_scores else 0.0

    # By category
    by_cat: dict[str, list] = {}
    for r in results:
        by_cat.setdefault(r["category"], []).append(r)

    metrics = {
        "total": total,
        "pass_rate_total": round(passed_total / total if total else 0.0, 4),
        "pass_rate_must": round(rate(must), 4),
        "pass_rate_should": round(rate(should), 4),
        "must_count": len(must),
        "should_count": len(should),
        "mrr_at_k": round(mrr, 4),
        "avg_top1_score": round(avg_top1, 4),
        "median_top1_score": round(med_top1, 4),
        "min_top1_score": round(min_top1, 4),
        "max_top1_score": round(max_top1, 4),
        "avg_latency_ms": round(mean([r["latency_ms"] for r in results]) if results else 0.0, 2),
        "by_category": {k: round(rate(v), 4) for k, v in sorted(by_cat.items())},
    }

    # Write JSON results
    out_json.write_text(
        json.dumps({"metrics": metrics, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Write Markdown report
    lines = []
    lines.append("# Kuntalaki Retrieval Evaluation Report\n\n")
    lines.append("## Summary\n\n")
    lines.append(f"- **Total questions**: {metrics['total']}\n")
    lines.append(f"- **MUST questions**: {metrics['must_count']}\n")
    lines.append(f"- **SHOULD questions**: {metrics['should_count']}\n\n")

    lines.append("## Pass Rates\n\n")
    lines.append(f"| Metric | Value |\n")
    lines.append(f"|--------|-------|\n")
    lines.append(f"| PASS rate (TOTAL) | **{metrics['pass_rate_total']:.1%}** |\n")
    lines.append(f"| PASS rate (MUST) | **{metrics['pass_rate_must']:.1%}** |\n")
    lines.append(f"| PASS rate (SHOULD) | **{metrics['pass_rate_should']:.1%}** |\n")
    lines.append(f"| MRR@k | **{metrics['mrr_at_k']:.3f}** |\n\n")

    lines.append("## Score Statistics\n\n")
    lines.append(f"| Metric | Value |\n")
    lines.append(f"|--------|-------|\n")
    lines.append(f"| Avg top-1 score | {metrics['avg_top1_score']:.3f} |\n")
    lines.append(f"| Median top-1 score | {metrics['median_top1_score']:.3f} |\n")
    lines.append(f"| Min top-1 score | {metrics['min_top1_score']:.3f} |\n")
    lines.append(f"| Max top-1 score | {metrics['max_top1_score']:.3f} |\n")
    lines.append(f"| Avg latency | {metrics['avg_latency_ms']:.1f} ms |\n\n")

    lines.append("## Pass Rate by Category\n\n")
    lines.append("| Category | Pass Rate |\n")
    lines.append("|----------|----------|\n")
    for cat, rate_val in sorted(metrics["by_category"].items()):
        lines.append(f"| {cat} | {rate_val:.1%} |\n")
    lines.append("\n")

    # Failed questions
    fails = [r for r in results if not r["passed"]]
    fails.sort(key=lambda x: (not x["must"], x["category"], x["id"]))

    if fails:
        lines.append("## Failed Questions\n\n")
        lines.append("| ID | Type | Category | Query |\n")
        lines.append("|----|------|----------|-------|\n")
        for r in fails:
            q_type = "MUST" if r["must"] else "SHOULD"
            query_short = r["query"][:50] + "..." if len(r["query"]) > 50 else r["query"]
            lines.append(f"| {r['id']} | {q_type} | {r['category']} | {query_short} |\n")
        lines.append("\n")

    # Quality gates
    lines.append("## Quality Gates\n\n")
    gate_a = metrics["pass_rate_must"] >= 0.95
    gate_b = metrics["pass_rate_total"] >= 0.90
    gate_c = metrics["avg_latency_ms"] < 150

    lines.append(f"- Gate A (MUST >= 95%): {'PASS' if gate_a else 'FAIL'} ({metrics['pass_rate_must']:.1%})\n")
    lines.append(f"- Gate B (TOTAL >= 90%): {'PASS' if gate_b else 'FAIL'} ({metrics['pass_rate_total']:.1%})\n")
    lines.append(f"- Gate C (Latency < 150ms): {'PASS' if gate_c else 'FAIL'} ({metrics['avg_latency_ms']:.1f} ms)\n")

    out_md.write_text("".join(lines), encoding="utf-8")

    # Print summary
    print("\n" + "=" * 60)
    print("EVALUATION COMPLETE")
    print("=" * 60)
    print(f"Total: {metrics['pass_rate_total']:.1%} ({passed_total}/{total})")
    print(f"MUST:  {metrics['pass_rate_must']:.1%}")
    print(f"MRR:   {metrics['mrr_at_k']:.3f}")
    print(f"Avg latency: {metrics['avg_latency_ms']:.1f} ms")
    print()
    print(f"Wrote: {out_json}")
    print(f"Wrote: {out_md}")


if __name__ == "__main__":
    main()

