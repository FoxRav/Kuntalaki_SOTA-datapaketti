"""
Build ChromaDB vector embeddings for Kirjanpitolaki.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install chromadb sentence-transformers")
    sys.exit(1)


def main() -> None:
    """Build embeddings for Kirjanpitolaki."""
    
    # Paths
    base_dir = Path(__file__).parent
    jsonl_path = base_dir / "analysis_layer" / "json" / "kirjanpitolaki-1336-1997.jsonl"
    chroma_path = base_dir / "analysis_layer" / "embeddings" / "chroma_db"
    
    if not jsonl_path.exists():
        print(f"ERROR: JSONL not found: {jsonl_path}")
        print("Run build_kirjanpitolaki.py first!")
        sys.exit(1)
    
    # Load records
    print(f"Loading records from {jsonl_path}")
    records: list[dict] = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    print(f"  Loaded {len(records)} records")
    
    # Initialize embedding model
    print("\nLoading embedding model: BAAI/bge-m3")
    model = SentenceTransformer("BAAI/bge-m3")
    
    # Create ChromaDB
    print(f"\nCreating ChromaDB at {chroma_path}")
    chroma_path.mkdir(parents=True, exist_ok=True)
    
    client = chromadb.PersistentClient(path=str(chroma_path))
    
    # Delete existing collection if exists
    try:
        client.delete_collection("kirjanpitolaki")
        print("  Deleted existing collection")
    except (ValueError, chromadb.errors.NotFoundError):
        pass
    
    collection = client.create_collection(
        name="kirjanpitolaki",
        metadata={"hnsw:space": "cosine"},
    )
    
    # Prepare documents
    print("\nPreparing documents...")
    documents: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []
    
    for record in records:
        # Create document text for embedding
        doc_text = f"{record['section_title']}. {record['text']}"
        documents.append(doc_text)
        
        # Metadata - ensure no None values (ChromaDB doesn't accept them)
        metadatas.append({
            "law": record["law"] or "",
            "law_id": record["law_id"] or "",
            "law_key": record["law_key"] or "",
            "node_id": record["node_id"] or "",
            "finlex_version": record["finlex_version"] or "",
            "chapter": record["chapter"] or "",
            "chapter_title": record["chapter_title"] or "",
            "section_id": record["section_id"] or "",
            "section_num": record["section_num"] or 0,
            "section_suffix": record.get("section_suffix") or "",
            "section_title": record["section_title"] or "",
            "moment": record["moment"] or "",
            "tags": json.dumps(record["tags"] or []),
            "anchors": json.dumps(record.get("anchors") or []),
            "in_force": bool(record["in_force"]),
        })
        
        ids.append(record["node_id"])
    
    # Generate embeddings in batches
    print("\nGenerating embeddings...")
    batch_size = 32
    all_embeddings: list[list[float]] = []
    
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        embeddings = model.encode(batch, normalize_embeddings=True)
        all_embeddings.extend(embeddings.tolist())
        print(f"  Processed {min(i + batch_size, len(documents))}/{len(documents)}")
    
    # Add to ChromaDB
    print("\nAdding to ChromaDB...")
    collection.add(
        documents=documents,
        embeddings=all_embeddings,
        metadatas=metadatas,
        ids=ids,
    )
    
    print(f"\nDone! Added {len(records)} documents to ChromaDB")
    print(f"Collection: kirjanpitolaki")
    print(f"Path: {chroma_path}")


if __name__ == "__main__":
    main()

