"""
Autofill cross-law expected values (v7).

Reads questions with expected_law_key + expected_anchor_terms,
queries the specific law index, and fills in the correct section_num + moment.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"Missing dependency: {e}")
    sys.exit(1)


# Configuration
EVAL_HARNESS_DIR = PROJECT_ROOT / "shared" / "eval_harness"
MIN_SCORE = 0.45  # Lower threshold for autofill

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


def load_index(law_key: str) -> chromadb.Collection | None:
    """Load a single law index."""
    config = LAW_INDICES.get(law_key)
    if not config:
        return None
    
    chroma_path = config["chroma_path"]
    if not chroma_path.exists():
        return None
    
    try:
        client = chromadb.PersistentClient(path=str(chroma_path))
        return client.get_collection(config["collection_name"])
    except Exception as e:
        print(f"  Warning: Could not load {law_key}: {e}")
        return None


def calculate_anchor_overlap(text: str, anchors: list[str], anchor_terms: list[str]) -> int:
    """Calculate overlap between anchor terms and document text/anchors."""
    text_lower = text.lower()
    doc_anchors_lower = [a.lower() for a in anchors]
    
    overlap = 0
    for term in anchor_terms:
        term_lower = term.lower()
        if term_lower in text_lower:
            overlap += 1
        elif any(term_lower in anchor for anchor in doc_anchors_lower):
            overlap += 1
    
    return overlap


def autofill_question(
    question: dict,
    model: SentenceTransformer,
    indices_cache: dict[str, chromadb.Collection],
) -> dict:
    """Autofill expected_any for a single question."""
    query = question.get("query", "")
    expected_law_key = question.get("expected_law_key", "")
    anchor_terms = question.get("expected_anchor_terms", [])
    
    # Get or load index
    if expected_law_key not in indices_cache:
        indices_cache[expected_law_key] = load_index(expected_law_key)
    
    collection = indices_cache.get(expected_law_key)
    if collection is None:
        return {
            **question,
            "autofill_status": "FAIL",
            "autofill_reason": f"Index not found: {expected_law_key}",
            "expected_any": [],
        }
    
    # Generate embedding and query
    embedding = model.encode([query], normalize_embeddings=True)[0].tolist()
    
    results = collection.query(
        query_embeddings=[embedding],
        n_results=10,
        include=["documents", "metadatas", "distances"],
    )
    
    if not results["documents"][0]:
        return {
            **question,
            "autofill_status": "FAIL",
            "autofill_reason": "No results from index",
            "expected_any": [],
        }
    
    # Rerank by anchor overlap if anchor_terms provided
    candidates = []
    for i, (doc, meta, dist) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    )):
        score = 1 - dist
        
        # Get anchors from metadata
        anchors_raw = meta.get("anchors", "[]")
        if isinstance(anchors_raw, str):
            try:
                anchors = json.loads(anchors_raw)
            except json.JSONDecodeError:
                anchors = []
        else:
            anchors = anchors_raw or []
        
        # Calculate anchor overlap
        overlap = calculate_anchor_overlap(doc, anchors, anchor_terms) if anchor_terms else 0
        
        candidates.append({
            "rank": i,
            "score": score,
            "overlap": overlap,
            "section_num": meta.get("section_num", 0),
            "moment": meta.get("moment", ""),
            "section_title": meta.get("section_title", ""),
            "doc_preview": doc[:100],
        })
    
    # Sort by overlap (desc), then by score (desc)
    candidates.sort(key=lambda x: (x["overlap"], x["score"]), reverse=True)
    
    best = candidates[0]
    
    # Check if best is good enough
    if best["overlap"] >= 1 or best["score"] >= MIN_SCORE:
        return {
            **question,
            "autofill_status": "OK",
            "autofill_score": best["score"],
            "autofill_overlap": best["overlap"],
            "expected_any": [{
                "law_key": expected_law_key,
                "section_num": int(best["section_num"]),
                "moment": int(best["moment"]) if str(best["moment"]).isdigit() else best["moment"],
            }],
        }
    else:
        return {
            **question,
            "autofill_status": "FAIL",
            "autofill_reason": f"Best hit too weak: score={best['score']:.3f}, overlap={best['overlap']}",
            "autofill_candidates": candidates[:3],
            "expected_any": [],
        }


def convert_v6_to_v7_input(question: dict) -> dict:
    """Convert v6 question format to v7 input format."""
    # Extract expected_law_key from expected_any
    expected_any = question.get("expected_any", [])
    expected_law_key = expected_any[0].get("law_key", "") if expected_any else ""
    
    # Extract anchor terms from query
    query = question.get("query", "")
    # Use simple word extraction as anchor terms
    words = re.findall(r'\b[a-zäöå]{4,}\b', query.lower())
    anchor_terms = list(set(words))[:5]  # Take top 5 unique words
    
    return {
        "id": question.get("id", ""),
        "type": question.get("type", "SHOULD"),
        "category": question.get("category", "cross_law"),
        "test_type": question.get("test_type", "cross_law"),
        "query": query,
        "expected_law_key": expected_law_key,
        "expected_anchor_terms": anchor_terms,
        "expected_none": question.get("expected_none", []),
        "notes": question.get("notes", ""),
    }


def main() -> None:
    """Run autofill for all cross-law question files."""
    print("=" * 60)
    print("Autofill Cross-Law Expected Values (v7)")
    print("=" * 60)
    
    # Load embedding model
    print("\nLoading embedding model...")
    model = SentenceTransformer("BAAI/bge-m3")
    
    # Cache for loaded indices
    indices_cache: dict[str, chromadb.Collection] = {}
    
    # Find all cross-law question files (v6 format)
    question_files = list(EVAL_HARNESS_DIR.glob("questions_cross_*.json"))
    # Exclude already autofilled files
    question_files = [f for f in question_files if ".autofill." not in f.name]
    
    total_ok = 0
    total_fail = 0
    
    for qf in question_files:
        print(f"\nProcessing: {qf.name}")
        
        with open(qf, encoding="utf-8") as f:
            data = json.load(f)
        
        questions = data.get("questions", [])
        autofilled_questions = []
        file_ok = 0
        file_fail = 0
        
        for q in questions:
            # Convert v6 to v7 input format first
            q_v7 = convert_v6_to_v7_input(q)
            
            # Run autofill
            result = autofill_question(q_v7, model, indices_cache)
            autofilled_questions.append(result)
            
            if result.get("autofill_status") == "OK":
                file_ok += 1
            else:
                file_fail += 1
                print(f"  FAIL: {result.get('id')} - {result.get('autofill_reason', 'Unknown')}")
        
        total_ok += file_ok
        total_fail += file_fail
        
        # Write autofilled file
        output_path = qf.with_suffix(".autofill.json")
        output_data = {
            "description": data.get("description", "") + " (autofilled v7)",
            "version": "7.0",
            "autofill_stats": {
                "ok": file_ok,
                "fail": file_fail,
            },
            "questions": autofilled_questions,
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"  OK: {file_ok}, FAIL: {file_fail}")
        print(f"  Output: {output_path.name}")
    
    print("\n" + "=" * 60)
    print(f"TOTAL: OK={total_ok}, FAIL={total_fail}")
    print("=" * 60)
    
    if total_fail > 0:
        print("\nWARNING: Some questions failed autofill. Review and fix before running eval.")


if __name__ == "__main__":
    main()

