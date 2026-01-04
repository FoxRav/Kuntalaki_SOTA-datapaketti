"""
Failure mining script for v7.2.

Analyzes cross-law eval failures and classifies them by type.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent
RESULTS_PATH = PROJECT_ROOT / "shared" / "eval_harness" / "results_cross_law.json"
REPORT_PATH = PROJECT_ROOT / "reports" / "v7_2_failures_baseline.md"


def classify_failure(question: dict) -> str:
    """
    Classify failure type:
    A) Wrong law (routing fail)
    B) Correct law, wrong section
    C) Correct section, wrong moment
    D) Correct hit exists in top-k but not in top-1
    """
    expected_any = question.get("expected_any", [])
    top1 = question.get("top1_result")
    pass_routing = question.get("pass_routing", False)
    pass_strict = question.get("pass_strict", False)
    top1_strict = question.get("top1_hit_strict", False)
    
    if not expected_any:
        return "X"  # No expected defined
    
    exp = expected_any[0]
    exp_law = exp.get("law_key", "")
    exp_section = int(exp.get("section_num", 0))
    exp_moment = str(exp.get("moment", ""))
    
    if not top1:
        return "A"  # No results at all
    
    top1_law = top1.get("law_key", "")
    top1_section = int(top1.get("section_num", 0))
    top1_moment = str(top1.get("moment", ""))
    
    # Type A: Wrong law
    if top1_law != exp_law:
        if pass_routing:
            # Correct law exists in top-k but not top-1
            return "D"
        return "A"
    
    # Type B: Correct law, wrong section
    if top1_section != exp_section:
        if pass_strict:
            # Correct hit exists in top-k
            return "D"
        return "B"
    
    # Type C: Correct section, wrong moment
    if top1_moment != exp_moment:
        if pass_strict:
            return "D"
        return "C"
    
    # Type D: Hit exists but not top-1 (already checked above)
    if pass_strict and not top1_strict:
        return "D"
    
    return "?"  # Should not happen for failures


def extract_keywords(query: str) -> list[str]:
    """Extract significant keywords from query."""
    stopwords = {"ja", "tai", "on", "ei", "kun", "jos", "miten", "mikä", "mitä", "missä"}
    words = query.lower().split()
    return [w for w in words if len(w) > 3 and w not in stopwords]


def main() -> None:
    """Generate failure mining report."""
    print("=" * 60)
    print("Failure Mining v7.2")
    print("=" * 60)
    
    # Load results
    with open(RESULTS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    
    questions = data["questions"]
    summary = data["summary"]
    pair_metrics = data["pair_metrics"]
    
    # Filter failures
    failures = [q for q in questions if not q.get("pass_strict")]
    
    print(f"\nTotal questions: {summary['total']}")
    print(f"STRICT failures: {len(failures)}")
    
    # Classify failures
    classified: dict[str, list[dict]] = defaultdict(list)
    for q in failures:
        fail_type = classify_failure(q)
        classified[fail_type].append(q)
    
    # Count failure types
    type_counts = {t: len(qs) for t, qs in classified.items()}
    print(f"\nFailure type distribution:")
    for t, count in sorted(type_counts.items()):
        print(f"  Type {t}: {count}")
    
    # Count failures per pair
    pair_fails: dict[str, int] = {}
    for q in failures:
        pair = q["source_file"].replace("questions_cross_kunta_", "").replace(".autofill.json", "")
        pair_fails[pair] = pair_fails.get(pair, 0) + 1
    
    print(f"\nFailures per pair:")
    for pair, count in sorted(pair_fails.items(), key=lambda x: x[1], reverse=True):
        total = pair_metrics.get(pair, {}).get("total", 20)
        print(f"  {pair.upper()}: {count}/{total} ({count/total*100:.0f}%)")
    
    # Extract top keywords from failures
    all_keywords: list[str] = []
    for q in failures:
        all_keywords.extend(extract_keywords(q["query"]))
    
    keyword_counts = Counter(all_keywords)
    top_keywords = keyword_counts.most_common(20)
    
    print(f"\nTop 20 keywords in failed queries:")
    for kw, count in top_keywords:
        print(f"  {kw}: {count}")
    
    # Generate markdown report
    lines = [
        "# v7.2 Failure Mining Report",
        "",
        f"**Generated from:** {RESULTS_PATH.name}",
        f"**Total questions:** {summary['total']}",
        f"**STRICT failures:** {len(failures)}",
        "",
        "## Failure Type Distribution",
        "",
        "| Type | Count | Description |",
        "|------|-------|-------------|",
        f"| A | {type_counts.get('A', 0)} | Wrong law (routing fail) |",
        f"| B | {type_counts.get('B', 0)} | Correct law, wrong section |",
        f"| C | {type_counts.get('C', 0)} | Correct section, wrong moment |",
        f"| D | {type_counts.get('D', 0)} | Correct hit in top-k, but not top-1 |",
        "",
        "## Failures per Pair",
        "",
        "| Pair | Failures | Total | Rate |",
        "|------|----------|-------|------|",
    ]
    
    for pair in ["hank", "kpa", "kpl", "oyl", "tila"]:
        total = pair_metrics.get(pair, {}).get("total", 20)
        fails = pair_fails.get(pair, 0)
        rate = fails / total * 100 if total > 0 else 0
        lines.append(f"| {pair.upper()} | {fails} | {total} | {rate:.0f}% |")
    
    lines.extend([
        "",
        "## Top 20 Keywords in Failed Queries",
        "",
        "| Keyword | Count |",
        "|---------|-------|",
    ])
    
    for kw, count in top_keywords:
        lines.append(f"| {kw} | {count} |")
    
    # Detailed failures by type
    for fail_type in ["A", "B", "C", "D"]:
        type_failures = classified.get(fail_type, [])
        if not type_failures:
            continue
        
        type_desc = {
            "A": "Wrong law (routing fail)",
            "B": "Correct law, wrong section",
            "C": "Correct section, wrong moment",
            "D": "Correct hit in top-k, but not top-1",
        }.get(fail_type, "Unknown")
        
        lines.extend([
            "",
            f"## Type {fail_type}: {type_desc} ({len(type_failures)})",
            "",
        ])
        
        for q in type_failures[:10]:  # Limit to 10 per type
            exp = q.get("expected_any", [{}])[0]
            top1 = q.get("top1_result", {}) or {}
            
            lines.append(f"### {q['id']}")
            lines.append(f"**Query:** {q['query']}")
            lines.append(f"**Expected:** {exp.get('law_key', 'N/A')} §{exp.get('section_num', '?')}.{exp.get('moment', '?')}")
            
            if top1:
                lines.append(f"**Got Top-1:** {top1.get('law_key', 'N/A')} §{top1.get('section_num', '?')}.{top1.get('moment', '?')} (score: {top1.get('score', 0):.4f})")
                lines.append(f"**Section Title:** {top1.get('section_title', 'N/A')}")
            else:
                lines.append("**Got Top-1:** None")
            
            lines.append("")
    
    # Write report
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"\nReport saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()

