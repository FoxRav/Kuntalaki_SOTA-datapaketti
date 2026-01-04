"""
Build ChromaDB vector embeddings for all laws.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"Missing dependency: {e}")
    sys.exit(1)


# Law configurations
LAWS = [
    {
        "law_key": "tilintarkastuslaki_1141_2015",
        "collection_name": "tilintarkastuslaki",
        "jsonl_path": PROJECT_ROOT / "laws" / "tilintarkastuslaki_1141_2015" / "analysis_layer" / "json" / "tilintarkastuslaki-1141-2015.jsonl",
        "chroma_path": PROJECT_ROOT / "laws" / "tilintarkastuslaki_1141_2015" / "analysis_layer" / "embeddings" / "chroma_db",
    },
    {
        "law_key": "hankintalaki_1397_2016",
        "collection_name": "hankintalaki",
        "jsonl_path": PROJECT_ROOT / "laws" / "hankintalaki_1397_2016" / "analysis_layer" / "json" / "hankintalaki-1397-2016.jsonl",
        "chroma_path": PROJECT_ROOT / "laws" / "hankintalaki_1397_2016" / "analysis_layer" / "embeddings" / "chroma_db",
    },
    {
        "law_key": "osakeyhtiolaki_624_2006",
        "collection_name": "osakeyhtiolaki",
        "jsonl_path": PROJECT_ROOT / "laws" / "osakeyhtiolaki_624_2006" / "analysis_layer" / "json" / "osakeyhtiolaki-624-2006.jsonl",
        "chroma_path": PROJECT_ROOT / "laws" / "osakeyhtiolaki_624_2006" / "analysis_layer" / "embeddings" / "chroma_db",
    },
]


def build_embeddings_for_law(
    config: dict,
    model: SentenceTransformer,
) -> int:
    """Build embeddings for a single law."""
    jsonl_path = config["jsonl_path"]
    chroma_path = config["chroma_path"]
    collection_name = config["collection_name"]
    
    print(f"\n{'='*60}")
    print(f"Processing: {config['law_key']}")
    print(f"{'='*60}")
    
    if not jsonl_path.exists():
        print(f"  ERROR: JSONL not found: {jsonl_path}")
        return 0
    
    # Load records
    print(f"  Loading records from {jsonl_path.name}")
    records: list[dict] = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    print(f"  Loaded {len(records)} records")
    
    # Create ChromaDB
    print(f"  Creating ChromaDB at {chroma_path}")
    chroma_path.mkdir(parents=True, exist_ok=True)
    
    client = chromadb.PersistentClient(path=str(chroma_path))
    
    # Delete existing collection if exists
    try:
        client.delete_collection(collection_name)
        print(f"  Deleted existing collection")
    except Exception:
        pass
    
    collection = client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    
    # Prepare documents
    print(f"  Preparing documents...")
    documents: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []
    
    for record in records:
        doc_text = f"{record['section_title']}. {record['text']}"
        documents.append(doc_text)
        
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
    print(f"  Generating embeddings...")
    batch_size = 32
    all_embeddings: list[list[float]] = []
    
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        embeddings = model.encode(batch, normalize_embeddings=True)
        all_embeddings.extend(embeddings.tolist())
        if (i + batch_size) % 128 == 0 or i + batch_size >= len(documents):
            print(f"    Processed {min(i + batch_size, len(documents))}/{len(documents)}")
    
    # Add to ChromaDB
    print(f"  Adding to ChromaDB...")
    collection.add(
        documents=documents,
        embeddings=all_embeddings,
        metadatas=metadatas,
        ids=ids,
    )
    
    print(f"  Done! Added {len(records)} documents")
    return len(records)


def main() -> None:
    """Build embeddings for all laws."""
    print("=" * 60)
    print("Building embeddings for all laws")
    print("=" * 60)
    
    # Load model once
    print("\nLoading embedding model: BAAI/bge-m3")
    model = SentenceTransformer("BAAI/bge-m3")
    
    total_docs = 0
    for config in LAWS:
        count = build_embeddings_for_law(config, model)
        total_docs += count
    
    print("\n" + "=" * 60)
    print(f"COMPLETE! Total documents indexed: {total_docs}")
    print("=" * 60)


if __name__ == "__main__":
    main()

