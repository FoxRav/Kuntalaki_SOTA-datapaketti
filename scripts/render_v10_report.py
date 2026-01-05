#!/usr/bin/env python3
"""
v10.1: Single-Source Report Renderer

Renders all v10 reports from the ONE source of truth:
    reports/v10_adversarial_results.json

This script is the ONLY place where metrics are calculated.
All other files (summary.md, failures.md, README) are derived from this.

Usage:
    python scripts/render_v10_report.py
"""

import json
from pathlib import Path
from typing import TypedDict


PROJECT_ROOT = Path(__file__).parent.parent
RESULTS_PATH = PROJECT_ROOT / "reports" / "v10_adversarial_results.json"
OUTPUT_DIR = PROJECT_ROOT / "reports"


class CaseResult(TypedDict):
    """v10.1 required fields per case."""
    case_id: str
    category: str
    query: str
    top1_law_key: str | None
    topk_law_keys: list[str]
    confusion_fail: bool
    hallucinated_evidence: bool
    version_drift: bool
    system_abstains: bool
    abstain_expected: bool
    latency_ms: float


def load_results(path: Path) -> list[dict]:
    """Load results JSON (single source of truth)."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_case(raw: dict) -> CaseResult:
    """
    Normalize raw result to v10.1 contract.
    Maps old field names to new contract.
    """
    expected = raw.get("expected", {}) if isinstance(raw.get("expected"), dict) else {}
    
    return {
        "case_id": raw.get("id", raw.get("case_id", "")),
        "category": raw.get("category", ""),
        "query": raw.get("query", ""),
        "top1_law_key": raw.get("top1_law", raw.get("top1_law_key")),
        "topk_law_keys": raw.get("actual_topk_laws", raw.get("topk_law_keys", [])),
        "confusion_fail": raw.get("confusion_fail", False),
        "hallucinated_evidence": raw.get("hallucinated_evidence", False),
        "version_drift": raw.get("version_drift", False),
        "system_abstains": raw.get("system_abstains", False),
        "abstain_expected": expected.get("must_abstain", False) if isinstance(expected, dict) else raw.get("abstain_expected", False),
        "latency_ms": raw.get("latency_ms", 0),
    }


def is_case_fail(case: CaseResult) -> bool:
    """
    v10.1 CASE_FAIL logic (locked):
    
    CASE_FAIL if ANY of:
    - hallucinated_evidence == true
    - version_drift == true
    - (confusion_fail == true AND category != ABSTAIN)
    - (abstain_expected == true AND system_abstains == false)
    """
    if case["hallucinated_evidence"]:
        return True
    if case["version_drift"]:
        return True
    if case["confusion_fail"] and case["category"] != "ABSTAIN":
        return True
    if case["abstain_expected"] and not case["system_abstains"]:
        return True
    return False


def calculate_gates(cases: list[CaseResult]) -> dict:
    """
    Calculate v10.1 gate metrics from normalized cases.
    This is the SINGLE place where metrics are calculated.
    """
    total = len(cases)
    
    # Count categories
    non_abstain_cases = [c for c in cases if not c["abstain_expected"]]
    abstain_cases = [c for c in cases if c["abstain_expected"]]
    
    # Gate 1: CONFUSION_FAIL_RATE
    confusion_fails = sum(1 for c in non_abstain_cases if c["confusion_fail"])
    confusion_fail_rate = confusion_fails / len(non_abstain_cases) if non_abstain_cases else 0
    
    # Gate 2: HALLU_EVIDENCE (count)
    hallu_evidence_count = sum(1 for c in cases if c["hallucinated_evidence"])
    
    # Gate 3: VERSION_DRIFT (count)
    version_drift_count = sum(1 for c in cases if c["version_drift"])
    
    # Gate 4: ABSTAIN_CORRECT (rate)
    abstain_correct = sum(1 for c in abstain_cases if c["system_abstains"])
    abstain_correct_rate = abstain_correct / len(abstain_cases) if abstain_cases else 1.0
    
    # Informational metrics
    case_fails = sum(1 for c in cases if is_case_fail(c))
    pass_rate = (total - case_fails) / total if total else 0
    avg_latency = sum(c["latency_ms"] for c in cases) / total if total else 0
    
    # Near misses: confusion_fail but expected law somewhere in topk
    # (This is informational only)
    near_misses = 0  # Would need more data to calculate
    
    return {
        # Gates (PASS/FAIL determining)
        "confusion_fail_rate": confusion_fail_rate,
        "confusion_fail_count": confusion_fails,
        "confusion_fail_gate": "PASS" if confusion_fail_rate <= 0.02 else "FAIL",
        
        "hallu_evidence_count": hallu_evidence_count,
        "hallu_evidence_gate": "PASS" if hallu_evidence_count == 0 else "FAIL",
        
        "version_drift_count": version_drift_count,
        "version_drift_gate": "PASS" if version_drift_count == 0 else "FAIL",
        
        "abstain_correct_rate": abstain_correct_rate,
        "abstain_correct_count": abstain_correct,
        "abstain_expected_count": len(abstain_cases),
        "abstain_gate": "PASS" if abstain_correct_rate >= 0.90 else "FAIL",
        
        # Informational (not gates)
        "pass_rate": pass_rate,
        "case_fails": case_fails,
        "total_cases": total,
        "avg_latency_ms": avg_latency,
        "near_misses": near_misses,
    }


def is_overall_pass(gates: dict) -> bool:
    """OVERALL PASS only if ALL gates pass."""
    return all([
        gates["confusion_fail_gate"] == "PASS",
        gates["hallu_evidence_gate"] == "PASS",
        gates["version_drift_gate"] == "PASS",
        gates["abstain_gate"] == "PASS",
    ])


def render_summary(cases: list[CaseResult], gates: dict, output_path: Path) -> None:
    """Render summary.md from calculated gates."""
    overall = "PASS" if is_overall_pass(gates) else "FAIL"
    
    lines = [
        "# v10 Adversarial Eval – Summary",
        "",
        "## Gates",
        "",
        f"- **CONFUSION_FAIL_RATE:** {gates['confusion_fail_rate']*100:.1f}% ({gates['confusion_fail_count']}/{gates['total_cases'] - gates['abstain_expected_count']}) → {gates['confusion_fail_gate']}",
        f"- **HALLU_EVIDENCE:** {gates['hallu_evidence_count']} → {gates['hallu_evidence_gate']}",
        f"- **VERSION_DRIFT:** {gates['version_drift_count']} → {gates['version_drift_gate']}",
        f"- **ABSTAIN_CORRECT:** {gates['abstain_correct_rate']*100:.1f}% ({gates['abstain_correct_count']}/{gates['abstain_expected_count']}) → {gates['abstain_gate']}",
        "",
        "## Overall verdict",
        "",
        f"**OVERALL: {overall}**",
        "",
        "## Info metrics (not gates)",
        "",
        f"- Pass rate: {gates['pass_rate']*100:.1f}%",
        f"- Case fails: {gates['case_fails']}",
        f"- Total cases: {gates['total_cases']}",
        f"- Avg latency: {gates['avg_latency_ms']:.0f} ms",
        "",
        "---",
        "",
        "*Generated by `render_v10_report.py` from `v10_adversarial_results.json`*",
    ]
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"  Summary: {output_path}")


def render_failures(cases: list[CaseResult], output_path: Path) -> None:
    """Render failures.md - ONLY CASE_FAIL cases."""
    failures = [c for c in cases if is_case_fail(c)]
    
    if not failures:
        lines = [
            "# v10 Adversarial Failures",
            "",
            "**No failures.**",
            "",
            "All cases passed.",
        ]
    else:
        lines = [
            "# v10 Adversarial Failures",
            "",
            f"**Total Failures:** {len(failures)}",
            "",
            "| Case | Category | Reason |",
            "|------|----------|--------|",
        ]
        
        for c in failures:
            reason = _get_failure_reason(c)
            lines.append(f"| {c['case_id']} | {c['category']} | {reason} |")
        
        lines.extend([
            "",
            "---",
            "",
            "*Generated by `render_v10_report.py` from `v10_adversarial_results.json`*",
        ])
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"  Failures: {output_path}")


def _get_failure_reason(case: CaseResult) -> str:
    """Get human-readable failure reason."""
    reasons = []
    if case["hallucinated_evidence"]:
        reasons.append("hallucinated_evidence")
    if case["version_drift"]:
        reasons.append("version_drift")
    if case["confusion_fail"] and case["category"] != "ABSTAIN":
        reasons.append(f"confusion_fail (top1={case['top1_law_key']})")
    if case["abstain_expected"] and not case["system_abstains"]:
        reasons.append("should_have_abstained")
    return "; ".join(reasons) if reasons else "unknown"


def render_metrics_csv(cases: list[CaseResult], gates: dict, output_path: Path) -> None:
    """Render optional metrics CSV."""
    lines = [
        "metric,value,gate",
        f"confusion_fail_rate,{gates['confusion_fail_rate']*100:.2f}%,{gates['confusion_fail_gate']}",
        f"hallu_evidence_count,{gates['hallu_evidence_count']},{gates['hallu_evidence_gate']}",
        f"version_drift_count,{gates['version_drift_count']},{gates['version_drift_gate']}",
        f"abstain_correct_rate,{gates['abstain_correct_rate']*100:.2f}%,{gates['abstain_gate']}",
        f"pass_rate,{gates['pass_rate']*100:.2f}%,info",
        f"avg_latency_ms,{gates['avg_latency_ms']:.0f},info",
    ]
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"  Metrics CSV: {output_path}")


def main() -> None:
    print("=" * 60)
    print("v10.1: Single-Source Report Renderer")
    print("=" * 60)
    
    if not RESULTS_PATH.exists():
        print(f"\nError: Results file not found: {RESULTS_PATH}")
        print("Run `python scripts/run_v10_adversarial_eval.py` first.")
        return
    
    print(f"\nLoading: {RESULTS_PATH}")
    raw_results = load_results(RESULTS_PATH)
    print(f"  Loaded {len(raw_results)} cases")
    
    print("\nNormalizing to v10.1 contract...")
    cases = [normalize_case(r) for r in raw_results]
    
    print("\nCalculating gates (single source)...")
    gates = calculate_gates(cases)
    
    print("\nGates:")
    print(f"  CONFUSION_FAIL_RATE: {gates['confusion_fail_rate']*100:.1f}% -> {gates['confusion_fail_gate']}")
    print(f"  HALLU_EVIDENCE:      {gates['hallu_evidence_count']} -> {gates['hallu_evidence_gate']}")
    print(f"  VERSION_DRIFT:       {gates['version_drift_count']} -> {gates['version_drift_gate']}")
    print(f"  ABSTAIN_CORRECT:     {gates['abstain_correct_rate']*100:.1f}% -> {gates['abstain_gate']}")
    
    overall = "PASS" if is_overall_pass(gates) else "FAIL"
    print(f"\n  OVERALL: {overall}")
    
    print("\nRendering reports...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    render_summary(cases, gates, OUTPUT_DIR / "v10_adversarial_summary.md")
    render_failures(cases, OUTPUT_DIR / "v10_adversarial_failures.md")
    render_metrics_csv(cases, gates, OUTPUT_DIR / "v10_adversarial_metrics.csv")
    
    print("\nDone!")
    print(f"\n{'='*60}")
    print(f"OVERALL: {overall}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

