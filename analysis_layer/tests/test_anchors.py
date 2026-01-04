"""
Test anchors field validation for v4 moment disambiguation.
"""

import json
from pathlib import Path

import pytest


@pytest.fixture
def jsonl_records() -> list[dict]:
    """Load JSONL records."""
    jsonl_path = Path(__file__).parent.parent / "json" / "kuntalaki_410-2015.jsonl"
    if not jsonl_path.exists():
        pytest.skip("JSONL file not found - run build_kuntalaki_json.py first")
    
    records = []
    for line in jsonl_path.read_text(encoding="utf-8").strip().split("\n"):
        records.append(json.loads(line))
    return records


def test_115_moments_have_anchors(jsonl_records: list[dict]) -> None:
    """All §115 moments must have non-empty anchors."""
    sec_115_records = [r for r in jsonl_records if r["section_id"] == "115"]
    
    assert len(sec_115_records) >= 3, "Expected at least 3 moments in §115"
    
    for record in sec_115_records:
        anchors = record.get("anchors", [])
        assert anchors, f"§115:{record['moment']} has empty anchors"
        assert len(anchors) >= 2, f"§115:{record['moment']} should have at least 2 anchors"


def test_115_anchors_are_distinct(jsonl_records: list[dict]) -> None:
    """§115 moment anchors must not be identical."""
    sec_115_records = [r for r in jsonl_records if r["section_id"] == "115"]
    
    anchor_sets = {}
    for record in sec_115_records:
        moment = record["moment"]
        anchors = frozenset(record.get("anchors", []))
        
        for other_moment, other_anchors in anchor_sets.items():
            if anchors == other_anchors:
                pytest.fail(
                    f"§115:{moment} and §115:{other_moment} have identical anchors"
                )
        
        anchor_sets[moment] = anchors


def test_110a_has_covid_anchors(jsonl_records: list[dict]) -> None:
    """§110a must have COVID-related anchors."""
    sec_110a_records = [r for r in jsonl_records if r["section_id"] == "110a"]
    
    assert sec_110a_records, "No §110a records found"
    
    covid_terms = {"covid", "korona", "pandemia", "poikkeus", "epidemia"}
    
    for record in sec_110a_records:
        anchors = set(a.lower() for a in record.get("anchors", []))
        overlap = anchors & covid_terms
        assert overlap, f"§110a:{record['moment']} missing COVID anchors"


def test_114_has_konserni_anchors(jsonl_records: list[dict]) -> None:
    """§114 must have konserni-related anchors."""
    sec_114_records = [r for r in jsonl_records if r["section_id"] == "114"]
    
    assert sec_114_records, "No §114 records found"
    
    konserni_terms = {"konserni", "konsernitilinpäätös", "kuntakonserni", "tytäryhteisö"}
    
    for record in sec_114_records:
        anchors = set(a.lower() for a in record.get("anchors", []))
        overlap = anchors & konserni_terms
        assert overlap, f"§114:{record['moment']} missing konserni anchors"


def test_anchors_field_exists(jsonl_records: list[dict]) -> None:
    """All records must have anchors field."""
    for record in jsonl_records:
        assert "anchors" in record, f"Missing anchors field in {record['node_id']}"
        assert isinstance(record["anchors"], list), f"anchors must be list in {record['node_id']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

