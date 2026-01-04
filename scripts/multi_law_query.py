"""
Multi-law query script.

Routes queries to appropriate law indices and merges results.
"""
from __future__ import annotations

import json
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

from shared.query_rules.law_router import route_query, calculate_k_per_law


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


def load_indices() -> dict[str, chromadb.Collection]:
    """Load all available law indices."""
    indices: dict[str, chromadb.Collection] = {}
    
    for law_key, config in LAW_INDICES.items():
        chroma_path = config["chroma_path"]
        if chroma_path.exists():
            try:
                client = chromadb.PersistentClient(path=str(chroma_path))
                collection = client.get_collection(config["collection_name"])
                indices[law_key] = collection
                print(f"Loaded: {law_key} ({collection.count()} docs)")
            except Exception as e:
                print(f"Warning: Could not load {law_key}: {e}")
        else:
            print(f"Warning: Index not found for {law_key}: {chroma_path}")
    
    return indices


def multi_law_query(
    query: str,
    indices: dict[str, chromadb.Collection],
    model: SentenceTransformer,
    total_k: int = 10,
    min_score: float = 0.50,
) -> list[dict]:
    """
    Query multiple law indices and merge results.
    
    Args:
        query: User query
        indices: Dictionary of law_key -> ChromaDB collection
        model: Sentence transformer model
        total_k: Total number of results to return
        min_score: Minimum score threshold
        
    Returns:
        List of result dicts sorted by score
    """
    # Route query to determine weights
    available_laws = list(indices.keys())
    weights = route_query(query, available_laws)
    
    print(f"\nQuery: {query}")
    print(f"Routing: {weights}")
    
    # Calculate k per law
    k_per_law = calculate_k_per_law(weights, total_k, min_k=2)
    
    # Generate embedding
    embedding = model.encode([query], normalize_embeddings=True)[0].tolist()
    
    # Query each law index
    all_results: list[dict] = []
    
    for law_key, k in k_per_law.items():
        if law_key not in indices:
            continue
            
        collection = indices[law_key]
        results = collection.query(
            query_embeddings=[embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        
        # Convert to result dicts
        for i, (doc, meta, dist) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )):
            score = 1 - dist  # Convert distance to score
            if score >= min_score:
                all_results.append({
                    "law_key": law_key,
                    "score": score,
                    "law": meta.get("law", ""),
                    "section_id": meta.get("section_id", ""),
                    "section_title": meta.get("section_title", ""),
                    "moment": meta.get("moment", ""),
                    "node_id": meta.get("node_id", ""),
                    "text": doc[:200] + "..." if len(doc) > 200 else doc,
                })
    
    # Sort by score and limit to total_k
    all_results.sort(key=lambda x: x["score"], reverse=True)
    return all_results[:total_k]


def main() -> None:
    """Interactive multi-law query."""
    print("=" * 60)
    print("Multi-Law Query System")
    print("=" * 60)
    
    # Load indices
    print("\nLoading indices...")
    indices = load_indices()
    
    if not indices:
        print("ERROR: No indices available!")
        sys.exit(1)
    
    print(f"\nAvailable laws: {list(indices.keys())}")
    
    # Load model
    print("\nLoading embedding model...")
    model = SentenceTransformer("BAAI/bge-m3")
    
    # Interactive loop
    print("\n" + "=" * 60)
    print("Enter queries (Ctrl+C to exit)")
    print("=" * 60)
    
    test_queries = [
        "kunnan talousarvion alijäämä",
        "tilinpäätöksen liitetiedot ja tase",
        "tilintarkastajan huomautus ja vastuuvapaus",
        "julkisen hankinnan kynnysarvo",
        "osakeyhtiön hallituksen vastuu",
        "konsernitilinpäätös ja tytäryhtiö",
    ]
    
    print("\nRunning test queries:\n")
    
    for query in test_queries:
        results = multi_law_query(query, indices, model, total_k=5)
        
        print(f"\nResults for: '{query}'")
        print("-" * 40)
        for i, r in enumerate(results[:3], 1):
            print(f"  {i}. [{r['law_key']}] § {r['section_id']}.{r['moment']} - {r['section_title']}")
            print(f"     Score: {r['score']:.4f}")
        print()


if __name__ == "__main__":
    main()

