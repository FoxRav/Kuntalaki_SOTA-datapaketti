import argparse
import json
import os
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / "analysis_layer"
AUDIT_DIR = LAYER / "audit"
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

def load_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception as e:
                raise SystemExit(f"[FAIL] JSONL parse error {path} line {i}: {e}")
    return rows

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--law", default="410/2015")
    args = ap.parse_args()

    jsonl_path = LAYER / "json" / "kuntalaki_410-2015.jsonl"
    lineage_path = LAYER / "lineage" / "kuntalaki_410-2015_versions.json"
    domain_filters_path = LAYER / "metadata" / "domain_filters.json"
    readme_path = LAYER / "README.md"

    if not jsonl_path.exists():
        raise SystemExit(f"[FAIL] Missing {jsonl_path}")
    if not lineage_path.exists():
        raise SystemExit(f"[FAIL] Missing {lineage_path}")
    if not domain_filters_path.exists():
        raise SystemExit(f"[FAIL] Missing {domain_filters_path}")

    rows = load_jsonl(jsonl_path)
    lineage = load_json(lineage_path)
    domain_filters = load_json(domain_filters_path)

    # 1) Node_id uniqueness
    node_ids = [r.get("node_id") for r in rows]
    missing_node_id = sum(1 for x in node_ids if not x)
    dup_count = sum(c-1 for c in Counter(node_ids).values() if c and c > 1)

    # 2) finlex_version coverage vs lineage
    # Support both formats: {"410/2015": [...]} or {"law_id": "410/2015", "versions": [...]}
    if args.law in lineage:
        lineage_versions = lineage[args.law]
    elif lineage.get("law_id") == args.law and "versions" in lineage:
        lineage_versions = lineage["versions"]
    else:
        raise SystemExit(f"[FAIL] Lineage missing key {args.law}")
    lineage_fin = {v.get("finlex") for v in lineage_versions}
    json_fin = {r.get("finlex_version") for r in rows}
    missing_in_lineage = sorted([v for v in json_fin if v not in lineage_fin])
    # also ensure lineage entries have source_xml
    lineage_missing_source_xml = sum(1 for v in lineage_versions if not v.get("source_xml"))

    # 3) section_id normalization checks
    bad_section = 0
    for r in rows:
        sid = r.get("section_id")
        sn = r.get("section_num")
        ss = r.get("section_suffix")
        if sid is None or sn is None:
            bad_section += 1
            continue
        expected = f"{sn}{ss or ''}"
        if str(sid) != str(expected):
            bad_section += 1

    # 4) Domain filter sanity
    talous = domain_filters.get("talous", {})
    required_tags = talous.get("required_tags", [])
    sections = talous.get("sections", [])
    # compute hitrate: how many rows match talous sections OR tags
    hits = 0
    for r in rows:
        rtags = set(r.get("tags") or [])
        if (r.get("section_id") in sections) or (rtags.intersection(required_tags)):
            hits += 1
    domain_filter_hitrate = hits / max(len(rows), 1)

    # 5) README presence check (light)
    readme_ok = readme_path.exists()

    metrics = {
        "ROWS": len(rows),
        "MISSING_NODE_ID": missing_node_id,
        "DUPLICATE_NODE_ID": dup_count,
        "MISSING_LINEAGE": len(missing_in_lineage),
        "MISSING_LINEAGE_VALUES": missing_in_lineage[:20],
        "LINEAGE_MISSING_SOURCE_XML": lineage_missing_source_xml,
        "BAD_SECTION_NORMALIZATION": bad_section,
        "DOMAIN_FILTER_HITRATE": round(domain_filter_hitrate, 4),
        "README_EXISTS": readme_ok,
    }

    (AUDIT_DIR / "audit_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown report
    report = []
    report.append("# Kuntalaki SOTA Audit Report\n")
    report.append(f"- Rows (momentit): **{metrics['ROWS']}**\n")
    report.append("## Invariantit\n")
    report.append(f"- MISSING_NODE_ID: **{metrics['MISSING_NODE_ID']}**\n")
    report.append(f"- DUPLICATE_NODE_ID: **{metrics['DUPLICATE_NODE_ID']}**\n")
    report.append(f"- BAD_SECTION_NORMALIZATION: **{metrics['BAD_SECTION_NORMALIZATION']}**\n")
    report.append(f"- MISSING_LINEAGE: **{metrics['MISSING_LINEAGE']}**\n")
    if metrics["MISSING_LINEAGE"]:
        report.append("### Missing finlex_version values (sample)\n")
        for v in metrics["MISSING_LINEAGE_VALUES"]:
            report.append(f"- {v}\n")
    report.append(f"- LINEAGE_MISSING_SOURCE_XML: **{metrics['LINEAGE_MISSING_SOURCE_XML']}**\n")
    report.append("## Domain filter\n")
    report.append(f"- DOMAIN_FILTER_HITRATE: **{metrics['DOMAIN_FILTER_HITRATE']}**\n")
    report.append("## Docs\n")
    report.append(f"- README_EXISTS: **{metrics['README_EXISTS']}**\n")

    (AUDIT_DIR / "audit_report.md").write_text("".join(report), encoding="utf-8")

    # Hard PASS/FAIL
    if metrics["MISSING_NODE_ID"] != 0: raise SystemExit("[FAIL] node_id missing")
    if metrics["DUPLICATE_NODE_ID"] != 0: raise SystemExit("[FAIL] node_id duplicates")
    if metrics["BAD_SECTION_NORMALIZATION"] != 0: raise SystemExit("[FAIL] section_id normalization errors")
    if metrics["MISSING_LINEAGE"] != 0: raise SystemExit("[FAIL] finlex_version not in lineage")
    if metrics["LINEAGE_MISSING_SOURCE_XML"] != 0: raise SystemExit("[FAIL] lineage entries missing source_xml")
    print("[PASS] SOTA audit passed. Reports in analysis_layer/audit/")

if __name__ == "__main__":
    main()
