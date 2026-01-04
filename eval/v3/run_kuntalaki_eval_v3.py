"""
Kuntalaki retrieval evaluation runner v3.

Laajennettu testausympäristö:
- k-sweep ja min_score-sweep
- top1_hit_rate, precision@1/@3
- hard negative -tuki (expected_none)
- stabiliteetti-testaus
- matrix-raportointi
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, median, stdev
from typing import TypedDict

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sentence_transformers import SentenceTransformer

from analysis_layer.vector_store.chroma_store import ChromaVectorStore
from analysis_layer.query_boost import apply_query_boost


class Question(TypedDict, total=False):
    id: str
    category: str
    must: bool
    query: str
    expected_any: list[dict[str, str]]
    expected_none: list[str] | None
    k: int
    min_score: float
    notes: str
    test_type: str


@dataclass
class EvalResult:
    """Evaluation result for a single question."""
    id: str
    category: str
    must: bool
    query: str
    expected_any: list[dict[str, str]]
    expected_none: list[str]
    test_type: str
    k: int
    min_score: float
    passed: bool
    hard_negative_violation: bool
    top1_hit: bool
    first_rank: int | None
    rr: float
    latency_ms: float
    hits: list[dict]


@dataclass
class MetricsResult:
    """Aggregated metrics for an evaluation run."""
    total: int
    pass_rate_total: float
    pass_rate_must: float
    pass_rate_should: float
    top1_hit_rate: float
    top1_hit_rate_must: float
    precision_at_1: float
    precision_at_3: float
    mrr_at_k: float
    hard_negative_violations: int
    avg_top1_score: float
    median_top1_score: float
    avg_latency_ms: float
    by_category: dict[str, float]
    by_test_type: dict[str, float]


def query_kuntalaki(
    model: SentenceTransformer,
    store: ChromaVectorStore,
    query: str,
    k: int = 5,
    apply_boost: bool = True,
) -> list[dict]:
    """Query the Kuntalaki index and return results."""
    embedding = model.encode([query], normalize_embeddings=True)[0]
    results = store.query(embedding.tolist(), n_results=k)

    hits = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        tags = meta.get("tags", [])
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except Exception:
                tags = []
        
        # v4: Parse anchors from metadata
        anchors = meta.get("anchors", [])
        if isinstance(anchors, str):
            try:
                anchors = json.loads(anchors)
            except Exception:
                anchors = []

        hits.append({
            "section_num": meta.get("section_id", ""),
            "moment": meta.get("moment", ""),
            "section_title": meta.get("section_title", ""),
            "node_id": meta.get("node_id", ""),
            "score": round(1 - dist, 4),
            "text": doc[:300],
            "anchors": anchors,  # v4: for anchor overlap
        })

    # SOTA: Apply query-time boosting for moment-level precision
    if apply_boost:
        hits = apply_query_boost(query, hits)

    return hits


def hit_matches_expected(hit: dict, expected: dict) -> bool:
    """Check if a hit matches an expected result."""
    sec = str(hit.get("section_num", "")).replace(" ", "").lower()
    mom = str(hit.get("moment", "")).strip()

    exp_sec = str(expected.get("section", "")).replace(" ", "").lower()
    exp_mom = str(expected.get("moment", "")).strip()

    return sec == exp_sec and (exp_mom == "" or mom == exp_mom)


def hit_matches_forbidden(hit: dict, forbidden_sections: list[str]) -> bool:
    """Check if a hit matches a forbidden section."""
    sec = str(hit.get("section_num", "")).replace(" ", "").lower()
    for forbidden in forbidden_sections:
        if sec == forbidden.replace(" ", "").lower():
            return True
    return False


def eval_one(
    q: Question,
    model: SentenceTransformer,
    store: ChromaVectorStore,
    k_override: int | None = None,
    min_score_override: float | None = None,
) -> EvalResult:
    """Evaluate a single question."""
    k = k_override if k_override is not None else int(q.get("k", 5))
    min_score = min_score_override if min_score_override is not None else float(q.get("min_score", 0.55))
    expected_none = q.get("expected_none", []) or []

    t0 = time.time()
    hits = query_kuntalaki(model, store, q["query"], k=k)
    dt = time.time() - t0

    # Find first matching hit
    first_rank = None
    passed = False

    for i, h in enumerate(hits, start=1):
        if float(h.get("score", 0.0)) < min_score:
            continue
        for exp in q.get("expected_any", []):
            if hit_matches_expected(h, exp):
                passed = True
                first_rank = i
                break
        if passed:
            break

    # Check top-1 hit (is first hit a correct one, ignoring min_score)
    top1_hit = False
    if hits:
        for exp in q.get("expected_any", []):
            if hit_matches_expected(hits[0], exp):
                top1_hit = True
                break

    # Check hard negative violations (forbidden section in top-1)
    hard_negative_violation = False
    if expected_none and hits:
        if hit_matches_forbidden(hits[0], expected_none):
            hard_negative_violation = True
            passed = False  # Auto-fail if forbidden section is top-1

    rr = 0.0 if first_rank is None else 1.0 / first_rank

    return EvalResult(
        id=q["id"],
        category=q.get("category", ""),
        must=bool(q.get("must", False)),
        query=q["query"],
        expected_any=q.get("expected_any", []),
        expected_none=expected_none,
        test_type=q.get("test_type", "base"),
        k=k,
        min_score=min_score,
        passed=passed,
        hard_negative_violation=hard_negative_violation,
        top1_hit=top1_hit,
        first_rank=first_rank,
        rr=rr,
        latency_ms=round(dt * 1000, 2),
        hits=hits,
    )


def calculate_metrics(results: list[EvalResult]) -> MetricsResult:
    """Calculate aggregated metrics from results."""
    total = len(results)
    passed_total = sum(1 for r in results if r.passed)

    must = [r for r in results if r.must]
    should = [r for r in results if not r.must]

    def rate(xs: list) -> float:
        return 0.0 if not xs else sum(1 for r in xs if r.passed) / len(xs)

    def top1_rate(xs: list) -> float:
        return 0.0 if not xs else sum(1 for r in xs if r.top1_hit) / len(xs)

    mrr = mean([r.rr for r in results]) if results else 0.0

    # Precision@1: what fraction of top-1 hits are correct
    top1_correct = sum(1 for r in results if r.top1_hit)
    precision_at_1 = top1_correct / total if total else 0.0

    # Precision@3: what fraction of top-3 positions have at least one correct
    p3_correct = 0
    for r in results:
        for h in r.hits[:3]:
            for exp in r.expected_any:
                if hit_matches_expected(h, exp):
                    p3_correct += 1
                    break
            else:
                continue
            break
    precision_at_3 = p3_correct / total if total else 0.0

    # Hard negative violations
    hard_neg_violations = sum(1 for r in results if r.hard_negative_violation)

    # Score stats
    top1_scores = [float(r.hits[0].get("score", 0.0)) for r in results if r.hits]
    avg_top1 = mean(top1_scores) if top1_scores else 0.0
    med_top1 = median(top1_scores) if top1_scores else 0.0

    # By category
    by_cat: dict[str, list] = {}
    for r in results:
        by_cat.setdefault(r.category, []).append(r)

    # By test type
    by_type: dict[str, list] = {}
    for r in results:
        by_type.setdefault(r.test_type, []).append(r)

    return MetricsResult(
        total=total,
        pass_rate_total=round(passed_total / total if total else 0.0, 4),
        pass_rate_must=round(rate(must), 4),
        pass_rate_should=round(rate(should), 4),
        top1_hit_rate=round(top1_rate(results), 4),
        top1_hit_rate_must=round(top1_rate(must), 4),
        precision_at_1=round(precision_at_1, 4),
        precision_at_3=round(precision_at_3, 4),
        mrr_at_k=round(mrr, 4),
        hard_negative_violations=hard_neg_violations,
        avg_top1_score=round(avg_top1, 4),
        median_top1_score=round(med_top1, 4),
        avg_latency_ms=round(mean([r.latency_ms for r in results]) if results else 0.0, 2),
        by_category={k: round(rate(v), 4) for k, v in sorted(by_cat.items())},
        by_test_type={k: round(rate(v), 4) for k, v in sorted(by_type.items())},
    )


def check_quality_gates(metrics: MetricsResult) -> dict[str, tuple[bool, str]]:
    """Check quality gates and return pass/fail status with details."""
    gates: dict[str, tuple[bool, str]] = {}

    # Gate 1: MUST >= 99%
    gate1_pass = metrics.pass_rate_must >= 0.99
    gates["Gate 1 (MUST >= 99%)"] = (gate1_pass, f"{metrics.pass_rate_must:.1%}")

    # Gate 1b: MUST Top-1 >= 80%
    gate1b_pass = metrics.top1_hit_rate_must >= 0.80
    gates["Gate 1b (MUST Top-1 >= 80%)"] = (gate1b_pass, f"{metrics.top1_hit_rate_must:.1%}")

    # Gate 2: SHOULD >= 95%
    gate2_pass = metrics.pass_rate_should >= 0.95
    gates["Gate 2 (SHOULD >= 95%)"] = (gate2_pass, f"{metrics.pass_rate_should:.1%}")

    # Gate 3: Category minimums >= 90%
    problem_cats = ["toimintakertomus", "covid-poikkeus", "arviointimenettely"]
    for cat in problem_cats:
        if cat in metrics.by_category:
            cat_pass = metrics.by_category[cat] >= 0.90
            gates[f"Gate 3 ({cat} >= 90%)"] = (cat_pass, f"{metrics.by_category[cat]:.1%}")

    # Gate 4: No hard negative violations
    gate4_pass = metrics.hard_negative_violations == 0
    gates["Gate 4 (No hard negative violations)"] = (gate4_pass, f"{metrics.hard_negative_violations}")

    # Gate 5: Latency < 150ms
    gate5_pass = metrics.avg_latency_ms < 150
    gates["Gate 5 (Latency < 150ms)"] = (gate5_pass, f"{metrics.avg_latency_ms:.1f} ms")

    return gates


def run_evaluation(
    questions: list[Question],
    model: SentenceTransformer,
    store: ChromaVectorStore,
    k_override: int | None = None,
    min_score_override: float | None = None,
    verbose: bool = True,
) -> tuple[list[EvalResult], MetricsResult]:
    """Run evaluation on all questions."""
    results: list[EvalResult] = []

    for i, q in enumerate(questions, 1):
        result = eval_one(q, model, store, k_override, min_score_override)
        results.append(result)
        if verbose:
            status = "PASS" if result.passed else "FAIL"
            if result.hard_negative_violation:
                status = "HARD-FAIL"
            print(f"  [{i}/{len(questions)}] {q['id']}: {status}", file=sys.stderr)

    metrics = calculate_metrics(results)
    return results, metrics


def run_matrix_evaluation(
    questions: list[Question],
    model: SentenceTransformer,
    store: ChromaVectorStore,
    k_values: list[int],
    min_score_values: list[float],
) -> dict[str, MetricsResult]:
    """Run matrix evaluation with multiple k and min_score values."""
    matrix_results: dict[str, MetricsResult] = {}

    for k in k_values:
        for min_score in min_score_values:
            config_name = f"k={k}_score={min_score}"
            print(f"\nRunning config: {config_name}", file=sys.stderr)
            _, metrics = run_evaluation(
                questions, model, store,
                k_override=k,
                min_score_override=min_score,
                verbose=False,
            )
            matrix_results[config_name] = metrics

    return matrix_results


def run_stability_test(
    questions: list[Question],
    model: SentenceTransformer,
    store: ChromaVectorStore,
    num_runs: int = 3,
) -> dict[str, float]:
    """Run stability test (multiple runs, measure variance)."""
    pass_rates: list[float] = []

    for i in range(num_runs):
        print(f"\nStability run {i + 1}/{num_runs}", file=sys.stderr)
        _, metrics = run_evaluation(questions, model, store, verbose=False)
        pass_rates.append(metrics.pass_rate_total)

    return {
        "avg_pass_rate": mean(pass_rates),
        "min_pass_rate": min(pass_rates),
        "max_pass_rate": max(pass_rates),
        "stdev_pass_rate": stdev(pass_rates) if len(pass_rates) > 1 else 0.0,
        "range_pct": (max(pass_rates) - min(pass_rates)) * 100,
    }


def write_report(
    results: list[EvalResult],
    metrics: MetricsResult,
    gates: dict[str, tuple[bool, str]],
    output_path: Path,
) -> None:
    """Write markdown evaluation report."""
    lines: list[str] = []

    lines.append("# Kuntalaki Retrieval Evaluation Report v3\n\n")
    lines.append("## Summary\n\n")
    lines.append(f"- **Total questions**: {metrics.total}\n")

    must_count = sum(1 for r in results if r.must)
    should_count = metrics.total - must_count
    lines.append(f"- **MUST questions**: {must_count}\n")
    lines.append(f"- **SHOULD questions**: {should_count}\n\n")

    lines.append("## Pass Rates\n\n")
    lines.append("| Metric | Value |\n")
    lines.append("|--------|-------|\n")
    lines.append(f"| PASS rate (TOTAL) | **{metrics.pass_rate_total:.1%}** |\n")
    lines.append(f"| PASS rate (MUST) | **{metrics.pass_rate_must:.1%}** |\n")
    lines.append(f"| PASS rate (SHOULD) | **{metrics.pass_rate_should:.1%}** |\n")
    lines.append(f"| Top-1 hit rate | **{metrics.top1_hit_rate:.1%}** |\n")
    lines.append(f"| Top-1 hit rate (MUST) | **{metrics.top1_hit_rate_must:.1%}** |\n")
    lines.append(f"| Precision@1 | **{metrics.precision_at_1:.1%}** |\n")
    lines.append(f"| Precision@3 | **{metrics.precision_at_3:.1%}** |\n")
    lines.append(f"| MRR@k | **{metrics.mrr_at_k:.3f}** |\n\n")

    lines.append("## Score Statistics\n\n")
    lines.append("| Metric | Value |\n")
    lines.append("|--------|-------|\n")
    lines.append(f"| Avg top-1 score | {metrics.avg_top1_score:.3f} |\n")
    lines.append(f"| Median top-1 score | {metrics.median_top1_score:.3f} |\n")
    lines.append(f"| Avg latency | {metrics.avg_latency_ms:.1f} ms |\n")
    lines.append(f"| Hard negative violations | {metrics.hard_negative_violations} |\n\n")

    lines.append("## Quality Gates\n\n")
    lines.append("| Gate | Status | Value |\n")
    lines.append("|------|--------|-------|\n")
    all_pass = True
    for gate_name, (passed, value) in gates.items():
        status = "PASS" if passed else "**FAIL**"
        if not passed:
            all_pass = False
        lines.append(f"| {gate_name} | {status} | {value} |\n")
    lines.append(f"\n**Overall**: {'ALL GATES PASS' if all_pass else 'SOME GATES FAIL'}\n\n")

    lines.append("## Pass Rate by Category\n\n")
    lines.append("| Category | Pass Rate |\n")
    lines.append("|----------|----------|\n")
    for cat, rate_val in sorted(metrics.by_category.items()):
        status = "" if rate_val >= 0.90 else " ⚠️"
        lines.append(f"| {cat} | {rate_val:.1%}{status} |\n")
    lines.append("\n")

    lines.append("## Pass Rate by Test Type\n\n")
    lines.append("| Test Type | Pass Rate |\n")
    lines.append("|-----------|----------|\n")
    for ttype, rate_val in sorted(metrics.by_test_type.items()):
        lines.append(f"| {ttype} | {rate_val:.1%} |\n")
    lines.append("\n")

    # Failed questions
    fails = [r for r in results if not r.passed]
    fails.sort(key=lambda x: (not x.must, x.category, x.id))

    if fails:
        lines.append("## Failed Questions\n\n")
        lines.append("| ID | Type | Category | Test Type | Query |\n")
        lines.append("|----|------|----------|-----------|-------|\n")
        for r in fails[:50]:  # Limit to 50
            q_type = "MUST" if r.must else "SHOULD"
            hn = " (HN-VIOL)" if r.hard_negative_violation else ""
            query_short = r.query[:40] + "..." if len(r.query) > 40 else r.query
            lines.append(f"| {r.id} | {q_type}{hn} | {r.category} | {r.test_type} | {query_short} |\n")
        if len(fails) > 50:
            lines.append(f"\n*... and {len(fails) - 50} more failed questions*\n")
        lines.append("\n")

    output_path.write_text("".join(lines), encoding="utf-8")


def write_matrix_report(
    matrix_results: dict[str, MetricsResult],
    output_path: Path,
) -> None:
    """Write matrix evaluation report."""
    lines: list[str] = []

    lines.append("# Kuntalaki Matrix Evaluation Report\n\n")
    lines.append("## Configuration Comparison\n\n")

    # Header
    lines.append("| Config | TOTAL | MUST | SHOULD | Top-1 | P@1 | MRR | Latency |\n")
    lines.append("|--------|-------|------|--------|-------|-----|-----|--------|\n")

    for config_name, m in sorted(matrix_results.items()):
        lines.append(
            f"| {config_name} | {m.pass_rate_total:.1%} | {m.pass_rate_must:.1%} | "
            f"{m.pass_rate_should:.1%} | {m.top1_hit_rate:.1%} | {m.precision_at_1:.1%} | "
            f"{m.mrr_at_k:.3f} | {m.avg_latency_ms:.0f}ms |\n"
        )

    lines.append("\n## Best Configuration\n\n")

    # Find best by pass_rate_total
    best_config = max(matrix_results.items(), key=lambda x: x[1].pass_rate_total)
    lines.append(f"- **Best overall**: {best_config[0]} ({best_config[1].pass_rate_total:.1%})\n")

    # Find best by MUST
    best_must = max(matrix_results.items(), key=lambda x: x[1].pass_rate_must)
    lines.append(f"- **Best MUST**: {best_must[0]} ({best_must[1].pass_rate_must:.1%})\n")

    # Find best by precision
    best_prec = max(matrix_results.items(), key=lambda x: x[1].precision_at_1)
    lines.append(f"- **Best Precision@1**: {best_prec[0]} ({best_prec[1].precision_at_1:.1%})\n")

    output_path.write_text("".join(lines), encoding="utf-8")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Kuntalaki Retrieval Evaluation v3")
    parser.add_argument("--matrix", action="store_true", help="Run matrix evaluation")
    parser.add_argument("--k-values", type=str, default="5", help="Comma-separated k values (default: 5)")
    parser.add_argument("--min-score-values", type=str, default="0.55", help="Comma-separated min_score values")
    parser.add_argument("--stability-runs", type=int, default=0, help="Number of stability test runs")
    parser.add_argument("--questions", type=str, default=None, help="Path to questions JSON file")
    args = parser.parse_args()

    root = Path(__file__).parent.parent.parent
    v3_dir = Path(__file__).parent

    # Determine questions file
    if args.questions:
        qpath = Path(args.questions)
    else:
        # Try v3 questions first, fall back to golden
        qpath = v3_dir / "questions_kuntalaki_v3.json"
        if not qpath.exists():
            qpath = root / "eval" / "questions_kuntalaki_golden.json"

    if not qpath.exists():
        print(f"ERROR: Questions file not found: {qpath}", file=sys.stderr)
        sys.exit(1)

    # Parse k and min_score values
    k_values = [int(x.strip()) for x in args.k_values.split(",")]
    min_score_values = [float(x.strip()) for x in args.min_score_values.split(",")]

    # Load questions
    questions: list[Question] = json.loads(qpath.read_text(encoding="utf-8"))
    print(f"Loaded {len(questions)} questions from {qpath}", file=sys.stderr)

    # Initialize search
    print("Loading model...", file=sys.stderr)
    model = SentenceTransformer("BAAI/bge-m3")

    chroma_path = root / "analysis_layer" / "embeddings" / "chroma_db"
    if not chroma_path.exists():
        print(f"ERROR: ChromaDB not found: {chroma_path}", file=sys.stderr)
        sys.exit(1)

    store = ChromaVectorStore(chroma_path, "kuntalaki")
    print(f"Connected to index. Documents: {store.count()}", file=sys.stderr)

    # Run matrix evaluation
    if args.matrix or len(k_values) > 1 or len(min_score_values) > 1:
        print("\nRunning matrix evaluation...", file=sys.stderr)
        matrix_results = run_matrix_evaluation(
            questions, model, store, k_values, min_score_values
        )

        # Write matrix report
        matrix_report_path = v3_dir / "report_matrix.md"
        write_matrix_report(matrix_results, matrix_report_path)
        print(f"\nWrote: {matrix_report_path}", file=sys.stderr)

        # Also write detailed JSON
        matrix_json_path = v3_dir / "kuntalaki_eval_matrix.json"
        matrix_data = {k: vars(v) for k, v in matrix_results.items()}
        matrix_json_path.write_text(
            json.dumps(matrix_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"Wrote: {matrix_json_path}", file=sys.stderr)

    # Run stability test
    if args.stability_runs > 1:
        print(f"\nRunning stability test ({args.stability_runs} runs)...", file=sys.stderr)
        stability_results = run_stability_test(questions, model, store, args.stability_runs)

        print("\nStability Results:", file=sys.stderr)
        print(f"  Avg pass rate: {stability_results['avg_pass_rate']:.1%}", file=sys.stderr)
        print(f"  Range: {stability_results['range_pct']:.2f}% points", file=sys.stderr)
        print(f"  Stdev: {stability_results['stdev_pass_rate']:.4f}", file=sys.stderr)

        # Check Gate 4 (stability)
        stable = stability_results["range_pct"] <= 2.0
        print(f"  Gate 4 (stability <= 2%): {'PASS' if stable else 'FAIL'}", file=sys.stderr)

    # Run standard evaluation
    print("\nRunning standard evaluation...", file=sys.stderr)
    results, metrics = run_evaluation(questions, model, store)
    gates = check_quality_gates(metrics)

    # Write outputs
    out_json = v3_dir / "kuntalaki_eval_v3_results.json"
    out_md = v3_dir / "report_kuntalaki_eval_v3.md"

    # JSON results
    results_data = {
        "metrics": vars(metrics),
        "gates": {k: {"passed": v[0], "value": v[1]} for k, v in gates.items()},
        "results": [vars(r) for r in results],
    }
    out_json.write_text(
        json.dumps(results_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    # Markdown report
    write_report(results, metrics, gates, out_md)

    # Print summary
    print("\n" + "=" * 60, file=sys.stderr)
    print("EVALUATION COMPLETE", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"Total: {metrics.pass_rate_total:.1%} ({int(metrics.pass_rate_total * metrics.total)}/{metrics.total})", file=sys.stderr)
    print(f"MUST:  {metrics.pass_rate_must:.1%}", file=sys.stderr)
    print(f"Top-1 hit rate: {metrics.top1_hit_rate:.1%}", file=sys.stderr)
    print(f"Precision@1: {metrics.precision_at_1:.1%}", file=sys.stderr)
    print(f"MRR:   {metrics.mrr_at_k:.3f}", file=sys.stderr)
    print(f"Hard negative violations: {metrics.hard_negative_violations}", file=sys.stderr)
    print(f"Avg latency: {metrics.avg_latency_ms:.1f} ms", file=sys.stderr)

    print("\nQuality Gates:", file=sys.stderr)
    for gate_name, (passed, value) in gates.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {gate_name}: {status} ({value})", file=sys.stderr)

    print(f"\nWrote: {out_json}", file=sys.stderr)
    print(f"Wrote: {out_md}", file=sys.stderr)


if __name__ == "__main__":
    main()

