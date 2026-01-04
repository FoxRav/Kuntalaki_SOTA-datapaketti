"""
Interaktiivinen hakutyökalu Kuntalaki-indeksiin.

Käyttö:
    python analysis_layer/query.py "kunnan talousarvion alijäämä"
    python analysis_layer/query.py --interactive
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sentence_transformers import SentenceTransformer

from analysis_layer.vector_store.chroma_store import ChromaVectorStore


def format_result(idx: int, doc: str, meta: dict, score: float) -> str:
    """Format a single search result."""
    lines = [
        f"\n{idx}. § {meta['section_id']}.{meta['moment']} - {meta['section_title']}",
        f"   Score: {score:.3f} | Luku: {meta['chapter']}",
        f"   {doc[:200]}...",
    ]
    # Parse and show tags
    tags = meta.get("tags", "[]")
    if isinstance(tags, str):
        tags = json.loads(tags)
    if tags:
        lines.append(f"   Tags: {', '.join(tags[:5])}")
    return "\n".join(lines)


def search(model, store, query: str, n_results: int = 5) -> None:
    """Execute search and print results."""
    print(f"\nQuery: '{query}'")
    print("-" * 60)

    embedding = model.encode([query], normalize_embeddings=True)[0]
    results = store.query(embedding.tolist(), n_results=n_results)

    if not results["documents"][0]:
        print("Ei tuloksia.")
        return

    for i, (doc, meta, dist) in enumerate(
        zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ),
        1,
    ):
        score = 1 - dist
        print(format_result(i, doc, meta, score))


def interactive_mode(model, store) -> None:
    """Run interactive search loop."""
    print("\n=== Kuntalaki Semantic Search ===")
    print("Kirjoita kysely ja paina Enter. Tyhjä rivi lopettaa.\n")

    while True:
        try:
            query = input("Kysely> ").strip()
            if not query:
                print("Lopetetaan.")
                break
            search(model, store, query)
        except KeyboardInterrupt:
            print("\nLopetetaan.")
            break
        except EOFError:
            break


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Kuntalaki semantic search")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("-n", "--num", type=int, default=5, help="Number of results")
    parser.add_argument("-i", "--interactive", action="store_true", help="Interactive mode")
    args = parser.parse_args()

    # Initialize
    print("Loading model...")
    model = SentenceTransformer("BAAI/bge-m3")

    base_path = Path(__file__).parent.parent
    chroma_path = base_path / "analysis_layer" / "embeddings" / "chroma_db"

    if not chroma_path.exists():
        print(f"ERROR: ChromaDB not found at {chroma_path}")
        print("Run: python analysis_layer/build_embeddings.py")
        sys.exit(1)

    store = ChromaVectorStore(chroma_path, "kuntalaki")
    print(f"Connected. Documents: {store.count()}")

    if args.interactive:
        interactive_mode(model, store)
    elif args.query:
        search(model, store, args.query, args.num)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

