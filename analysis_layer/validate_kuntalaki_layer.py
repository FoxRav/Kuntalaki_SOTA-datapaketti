import json
import os
import re
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]  # project root
XML_ROOT = ROOT / "finlex_statute_consolidated" / "akn" / "fi" / "act" / "statute-consolidated"
LAYER = ROOT / "analysis_layer"

JSON_PATH = LAYER / "json" / "kuntalaki_410-2015.json"
JSONL_PATH = LAYER / "json" / "kuntalaki_410-2015.jsonl"
LINEAGE_PATH = LAYER / "lineage" / "kuntalaki_410-2015_versions.json"
META_PATH = LAYER / "metadata" / "kuntalaki_410-2015_meta.json"

REQUIRED_KEYS = {
    "law", "law_id", "law_key", "finlex_version", "node_id",
    "part", "chapter", "chapter_title",
    "section_id", "section_num", "section_title",
    "moment", "text",
    "effective_from", "in_force",
    "tags", "source",
}
REQUIRED_SOURCE_KEYS = {"xml_path", "finlex_url", "xpath"}

def fail(msg: str):
    raise SystemExit(f"[FAIL] {msg}")

def ok(msg: str):
    print(f"[OK] {msg}")

def find_fin_versions():
    # Expect something like: .../2015/410/fin@20230780/main.xml
    versions = []
    if not XML_ROOT.exists():
        fail(f"XML root not found: {XML_ROOT}")
    for p in XML_ROOT.rglob("main.xml"):
        s = str(p).replace("\\", "/")
        m = re.search(r"/(\d{4})/(\d+)/fin@([^/]+)/main\.xml$", s)
        if m:
            year, lawnum, fin = m.group(1), m.group(2), m.group(3)
            if lawnum == "410":  # Kuntalaki
                versions.append((fin, p))
    versions.sort(key=lambda x: x[0])
    return versions

def load_jsonl(path: Path):
    if not path.exists():
        fail(f"Missing JSONL: {path}")
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception as e:
                fail(f"JSONL parse error at line {i}: {e}")
    return rows

def load_json(path: Path):
    if not path.exists():
        fail(f"Missing JSON: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def load_lineage(path: Path):
    if not path.exists():
        fail(f"Missing lineage: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def check_schema(rows):
    if not rows:
        fail("No rows in JSONL")
    for idx, r in enumerate(rows[:50]):  # sample first 50
        missing = REQUIRED_KEYS - set(r.keys())
        if missing:
            fail(f"Missing keys in row {idx}: {sorted(missing)}")
        if not isinstance(r.get("source"), dict):
            fail(f"source not dict in row {idx}")
        smiss = REQUIRED_SOURCE_KEYS - set(r["source"].keys())
        if smiss:
            fail(f"Missing source keys in row {idx}: {sorted(smiss)}")
        if not r.get("text") or not str(r["text"]).strip():
            fail(f"Empty text in row {idx}")
    ok("Schema sample looks OK (first 50 rows)")

def check_uniqueness(rows):
    seen = set()
    dup = 0
    for r in rows:
        # Use node_id for uniqueness (SOTA)
        node_id = r.get("node_id")
        if node_id in seen:
            dup += 1
        seen.add(node_id)
    if dup:
        fail(f"Duplicate node_id keys: {dup}")
    ok("Uniqueness OK (node_id unique)")

def check_finlex_versions_match(rows, versions):
    xml_fins = {f"fin@{fin}" for fin, _ in versions}
    json_fins = {r.get("finlex_version") for r in rows}
    # allow subset, but warn if json contains finlex not in xml tree
    extra = {v for v in json_fins if v and v not in xml_fins}
    if extra:
        fail(f"JSON contains finlex_version not found in XML tree: {sorted(extra)}")
    ok("finlex_version values are consistent with XML tree")

def check_xpath_resolves(sample_row, base_xml_root):
    # Minimal check: confirm xml_path exists and xpath is non-empty.
    sp = sample_row["source"]["xml_path"]
    xp = sample_row["source"]["xpath"]
    if not sp or not xp:
        fail("Empty source.xml_path or source.xpath")
    xml_path = base_xml_root / Path(sp)
    if not xml_path.exists():
        # allow if xml_path is already absolute-ish; try ROOT join
        xml_path = ROOT / Path(sp)
    if not xml_path.exists():
        fail(f"xml_path does not exist: {sp}")
    # Real XPath validation in ElementTree is limited; do best-effort:
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        # Remove namespaces if needed for naive find; at least ensure tree parses.
        ok(f"XML parses OK: {xml_path}")
    except Exception as e:
        fail(f"Cannot parse XML at {xml_path}: {e}")
    # We can't reliably evaluate complex XPath with namespaces using stdlib,
    # but we can at least assert it's not placeholder and points to something meaningful.
    if "akomaNtoso" not in xp and "/" not in xp:
        fail(f"xpath looks suspicious: {xp}")
    ok("Basic xpath sanity OK (not fully evaluated)")

def main():
    versions = find_fin_versions()
    ok(f"Found {len(versions)} fin@ versions for 410/2015 under XML tree")
    if len(versions) == 0:
        fail("No versions found; check directory structure")

    rows = load_jsonl(JSONL_PATH)
    ok(f"Loaded JSONL rows: {len(rows)}")

    # Optional: JSON array file existence check
    if JSON_PATH.exists():
        arr = load_json(JSON_PATH)
        if isinstance(arr, list) and len(arr) != len(rows):
            print(f"[WARN] JSON array length {len(arr)} != JSONL length {len(rows)}")
        else:
            ok("JSON array exists and length matches JSONL (or JSON not list)")
    else:
        print("[WARN] JSON array file missing (ok if you only use JSONL)")

    check_schema(rows)
    check_uniqueness(rows)
    check_finlex_versions_match(rows, versions)

    # lineage check
    lineage = load_lineage(LINEAGE_PATH)
    # Support both formats: {"410/2015": [...]} or {"law_id": "410/2015", "versions": [...]}
    if "410/2015" in lineage:
        versions_list = lineage["410/2015"]
    elif lineage.get("law_id") == "410/2015" and "versions" in lineage:
        versions_list = lineage["versions"]
    else:
        fail("Lineage missing key '410/2015' or 'versions'")
    ok(f"Lineage has {len(versions_list)} entries")

    # meta check
    if META_PATH.exists():
        meta = load_json(META_PATH)
        ok("Meta file exists")
        # basic sanity
        if meta.get("law_id") and meta["law_id"] != "410/2015":
            print("[WARN] meta.law_id != 410/2015")
    else:
        print("[WARN] Meta file missing")

    # xpath sanity check on a sample row
    check_xpath_resolves(rows[0], XML_ROOT)

    print("\n[DONE] Validation completed. Fix any FAIL/WARN above.")

if __name__ == "__main__":
    main()
