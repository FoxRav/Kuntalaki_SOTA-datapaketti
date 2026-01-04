"""
Kuntalaki embedding-indeksin rakentaminen ChromaDB:llä.

Käyttää BAAI/bge-m3 -mallia, joka on optimoitu monikieliselle tekstille.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sentence_transformers import SentenceTransformer

from analysis_layer.vector_store.chroma_store import ChromaVectorStore


def load_records(jsonl_path: Path) -> list[dict]:
    """Load records from JSONL file."""
    records = []
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def build_document_text(record: dict) -> str:
    """Build searchable document text from record.

    Includes section title for better semantic matching.
    """
    return f"§ {record['section_id']} {record['section_title']}: {record['text']}"


def main() -> None:
    """Build ChromaDB index with BGE-M3 embeddings."""
    base_path = Path(__file__).parent.parent
    jsonl_path = base_path / "analysis_layer" / "json" / "kuntalaki_410-2015.jsonl"

    if not jsonl_path.exists():
        print(f"ERROR: JSONL file not found: {jsonl_path}")
        print("Run build_kuntalaki_json.py first.")
        sys.exit(1)

    # Load records
    print(f"Loading records from {jsonl_path}...")
    records = load_records(jsonl_path)
    print(f"Loaded {len(records)} records")

    # Initialize embedding model
    print("\nLoading BAAI/bge-m3 model (this may take a moment on first run)...")
    start_time = time.time()
    model = SentenceTransformer("BAAI/bge-m3")
    print(f"Model loaded in {time.time() - start_time:.1f}s")

    # Prepare documents for embedding
    print("\nPreparing documents...")
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    for record in records:
        # Unique ID: use node_id from SOTA schema
        doc_id = record["node_id"]
        ids.append(doc_id)

        # Document text for embedding
        doc_text = build_document_text(record)
        documents.append(doc_text)

        # Metadata for filtering and display (SOTA fields)
        metadatas.append({
            "law": record["law"],
            "law_id": record["law_id"],
            "law_key": record["law_key"],
            "finlex_version": record["finlex_version"],
            "node_id": record["node_id"],
            "part": record["part"],
            "chapter": record["chapter"],
            "chapter_title": record["chapter_title"],
            "section_id": record["section_id"],
            "section_num": record["section_num"],
            "section_suffix": record.get("section_suffix") or "",
            "section_title": record["section_title"],
            "moment": record["moment"],
            "tags": record["tags"],
            "anchors": record.get("anchors", []),  # v4: moment-specific anchors
            "in_force": record["in_force"],
        })

    # Generate embeddings
    print(f"\nGenerating embeddings for {len(documents)} documents...")
    start_time = time.time()
    embeddings = model.encode(
        documents,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    print(f"Embeddings generated in {time.time() - start_time:.1f}s")

    # Initialize ChromaDB
    chroma_path = base_path / "analysis_layer" / "embeddings" / "chroma_db"
    print(f"\nInitializing ChromaDB at {chroma_path}...")

    store = ChromaVectorStore(
        persist_directory=chroma_path,
        collection_name="kuntalaki",
    )

    # Clear existing data and add new
    try:
        store.delete_collection()
        store = ChromaVectorStore(
            persist_directory=chroma_path,
            collection_name="kuntalaki",
        )
    except Exception:
        pass  # Collection might not exist yet

    print("Adding documents to ChromaDB...")
    start_time = time.time()
    store.add_documents(
        ids=ids,
        documents=documents,
        embeddings=embeddings.tolist(),
        metadatas=metadatas,
    )
    print(f"Documents added in {time.time() - start_time:.1f}s")

    # Verify
    count = store.count()
    print(f"\n[OK] Index built successfully!")
    print(f"     Documents in index: {count}")
    print(f"     Location: {chroma_path}")

    # Test query
    print("\n--- Test Query ---")
    test_query = "kunnan talousarvion alijäämä"
    print(f"Query: '{test_query}'")

    query_embedding = model.encode([test_query], normalize_embeddings=True)[0]
    results = store.query(query_embedding.tolist(), n_results=3)

    for i, (doc, meta, dist) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    )):
        print(f"\n{i+1}. § {meta['section_id']}.{meta['moment']} {meta['section_title']}")
        print(f"   Score: {1 - dist:.3f}")
        print(f"   Text: {doc[:150]}...")


if __name__ == "__main__":
    main()

