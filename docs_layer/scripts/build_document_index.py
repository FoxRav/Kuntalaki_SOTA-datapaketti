#!/usr/bin/env python3
"""
v9.1: Build Document Index for financial statements.

Indexes document graph nodes (PARA, TABLE, SECTION) into ChromaDB for
hybrid retrieval.

Usage:
    python docs_layer/scripts/build_document_index.py --graph <graph_dir> --output <chroma_dir>
"""

import argparse
import json
from pathlib import Path

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Install: pip install chromadb sentence-transformers")
    exit(1)


# Indexable node types (skip DOC, PAGE which are structural only)
INDEXABLE_TYPES = {"SECTION", "PARA", "TABLE", "ROW", "METRIC"}

# Minimum text length to index
MIN_TEXT_LENGTH = 20


def load_graph_nodes(graph_dir: Path) -> list[dict]:
    """Load nodes from graph JSONL."""
    nodes_path = graph_dir / "nodes.jsonl"
    nodes = []
    with open(nodes_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                nodes.append(json.loads(line))
    return nodes


def filter_indexable_nodes(nodes: list[dict]) -> list[dict]:
    """Filter nodes that should be indexed."""
    indexable = []
    for node in nodes:
        if node["node_type"] not in INDEXABLE_TYPES:
            continue
        
        # Must have text content
        text = node.get("text", "").strip()
        title = node.get("title", "").strip()
        content = f"{title} {text}".strip()
        
        if len(content) < MIN_TEXT_LENGTH:
            continue
        
        indexable.append(node)
    
    return indexable


def build_document_text(node: dict) -> str:
    """Build the text to embed for a node."""
    parts = []
    
    # Add title
    if node.get("title"):
        parts.append(node["title"])
    
    # Add text content
    if node.get("text"):
        parts.append(node["text"])
    
    # For TABLE/ROW, include cell data
    if node["node_type"] in ("TABLE", "ROW"):
        cells = node.get("metadata", {}).get("cells", [])
        if cells:
            parts.append(" | ".join(str(c) for c in cells))
    
    # For METRIC, include value
    if node["node_type"] == "METRIC":
        value = node.get("metadata", {}).get("value")
        unit = node.get("metadata", {}).get("unit", "")
        if value is not None:
            parts.append(f"Arvo: {value} {unit}")
    
    return " ".join(parts)


def build_metadata(node: dict) -> dict:
    """Build metadata for ChromaDB."""
    return {
        "node_id": node["node_id"],
        "node_type": node["node_type"],
        "city": node["city"],
        "year": node["year"],
        "title": node.get("title", ""),
        "page_num": node.get("page_num") or 0,
        "parent_id": node.get("parent_id", ""),
    }


def build_index(
    nodes: list[dict],
    output_dir: Path,
    collection_name: str,
    model: SentenceTransformer,
) -> None:
    """Build ChromaDB index from document nodes."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize ChromaDB
    client = chromadb.PersistentClient(path=str(output_dir))
    
    # Delete existing collection if exists
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass
    
    collection = client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    
    print(f"Building index for {len(nodes)} nodes...")
    
    # Prepare data
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []
    
    for node in nodes:
        doc_text = build_document_text(node)
        if len(doc_text.strip()) < MIN_TEXT_LENGTH:
            continue
        
        ids.append(node["node_id"])
        documents.append(doc_text)
        metadatas.append(build_metadata(node))
    
    print(f"Generating embeddings for {len(documents)} documents...")
    
    # Generate embeddings in batches
    batch_size = 64
    all_embeddings: list[list[float]] = []
    
    for i in range(0, len(documents), batch_size):
        batch = documents[i : i + batch_size]
        embeddings = model.encode(batch, normalize_embeddings=True)
        all_embeddings.extend(embeddings.tolist())
    
    # Add to collection
    collection.add(
        ids=ids,
        embeddings=all_embeddings,
        documents=documents,
        metadatas=metadatas,
    )
    
    print(f"Indexed {len(ids)} documents to {output_dir}")
    
    # Write summary
    summary = {
        "collection_name": collection_name,
        "document_count": len(ids),
        "node_types": {},
    }
    for meta in metadatas:
        nt = meta["node_type"]
        summary["node_types"][nt] = summary["node_types"].get(nt, 0) + 1
    
    summary_path = output_dir / "index_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"Summary: {summary_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build document index")
    parser.add_argument("--graph", "-g", required=True, help="Path to graph directory")
    parser.add_argument("--output", "-o", required=True, help="Output directory for ChromaDB")
    parser.add_argument("--collection", "-c", default="documents", help="Collection name")
    args = parser.parse_args()
    
    graph_dir = Path(args.graph)
    output_dir = Path(args.output)
    
    if not (graph_dir / "nodes.jsonl").exists():
        print(f"Error: nodes.jsonl not found in {graph_dir}")
        return
    
    print(f"Loading graph from {graph_dir}")
    nodes = load_graph_nodes(graph_dir)
    print(f"Loaded {len(nodes)} nodes")
    
    indexable = filter_indexable_nodes(nodes)
    print(f"Indexable nodes: {len(indexable)}")
    
    print("\nLoading embedding model (BAAI/bge-m3)...")
    model = SentenceTransformer("BAAI/bge-m3")
    
    build_index(indexable, output_dir, args.collection, model)
    
    print("\nDone!")


if __name__ == "__main__":
    main()

