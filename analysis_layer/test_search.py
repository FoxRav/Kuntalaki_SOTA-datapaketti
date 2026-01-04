"""Test search functionality."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sentence_transformers import SentenceTransformer

from analysis_layer.vector_store.chroma_store import ChromaVectorStore


def main() -> None:
    """Test search query."""
    print("Loading model...")
    model = SentenceTransformer("BAAI/bge-m3")

    print("Connecting to ChromaDB...")
    base_path = Path(__file__).parent.parent
    store = ChromaVectorStore(
        base_path / "analysis_layer" / "embeddings" / "chroma_db",
        "kuntalaki",
    )
    print(f"Documents in index: {store.count()}")

    print()
    print("--- Test Query 1: Talousarvio ---")
    query = "kunnan talousarvion alijaama ja kattaminen"
    print(f"Query: {query}")

    embedding = model.encode([query], normalize_embeddings=True)[0]
    results = store.query(embedding.tolist(), n_results=5)

    for i, (doc, meta, dist) in enumerate(
        zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )
    ):
        section = meta["section_id"]
        moment = meta["moment"]
        title = meta["section_title"]
        score = 1 - dist
        print(f"\n{i+1}. {section}.{moment} mom. - {title}")
        print(f"   Score: {score:.3f}")
        print(f"   {doc[:150]}...")

    print()
    print("--- Test Query 2: Arviointimenettely ---")
    query = "erityisen vaikeassa taloudellisessa asemassa oleva kunta"
    print(f"Query: {query}")

    embedding = model.encode([query], normalize_embeddings=True)[0]
    results = store.query(embedding.tolist(), n_results=3)

    for i, (doc, meta, dist) in enumerate(
        zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )
    ):
        section = meta["section_id"]
        moment = meta["moment"]
        title = meta["section_title"]
        score = 1 - dist
        print(f"\n{i+1}. {section}.{moment} mom. - {title}")
        print(f"   Score: {score:.3f}")
        print(f"   {doc[:150]}...")


if __name__ == "__main__":
    main()

