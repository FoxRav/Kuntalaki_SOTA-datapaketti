#!/usr/bin/env python3
"""
v9.2: Law↔Document Mapping Engine

Maps legal nodes (from v8 legal graph) to document nodes (from v9 doc graph).
Creates mapping edges: REQUIRES_DISCLOSURE, GOVERNS, EVIDENCED_BY, RISK_FLAG.

Usage:
    python docs_layer/scripts/map_law_to_doc.py --law-hits <hits_json> --doc-index <chroma_dir> --output <output_json>
    
    # Interactive mode:
    python docs_layer/scripts/map_law_to_doc.py --interactive --doc-index <chroma_dir>
"""

import argparse
import json
from pathlib import Path
from typing import TypedDict

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Install: pip install chromadb sentence-transformers")
    exit(1)


class MappingEdge(TypedDict):
    """Edge connecting law node to document node."""
    law_node_id: str
    doc_node_id: str
    edge_type: str  # REQUIRES_DISCLOSURE, GOVERNS, EVIDENCED_BY, RISK_FLAG
    score: float
    evidence_text: str
    context: str


class EvidenceBundle(TypedDict):
    """Bundle of evidence from document for a legal requirement."""
    law_node_id: str
    law_section: str
    doc_nodes: list[dict]
    mapping_edges: list[MappingEdge]


# Mapping rules: law section patterns to document section patterns
# These are deterministic rules for known mappings
MAPPING_RULES = {
    # Kuntalaki 113 (tilinpäätös) → Tuloslaskelma, Tase, Rahoituslaskelma
    "kuntalaki_410_2015:113": {
        "doc_sections": ["tuloslaskelma", "tase", "rahoituslaskelma"],
        "edge_type": "GOVERNS",
    },
    # Kuntalaki 114 (konsernitilinpäätös) → Konsernitilinpäätös
    "kuntalaki_410_2015:114": {
        "doc_sections": ["konsernitilinpäätös", "konserni"],
        "edge_type": "GOVERNS",
    },
    # Kuntalaki 115 (toimintakertomus) → Toimintakertomus
    "kuntalaki_410_2015:115": {
        "doc_sections": ["toimintakertomus"],
        "edge_type": "REQUIRES_DISCLOSURE",
    },
    # Kuntalaki 115:1 (sisäinen valvonta) → Sisäinen valvonta
    "kuntalaki_410_2015:115:1": {
        "doc_sections": ["sisäinen_valvonta", "riskienhallinta"],
        "edge_type": "REQUIRES_DISCLOSURE",
    },
    # Kuntalaki 118 (arviointimenettely) → Talouden tunnusluvut
    "kuntalaki_410_2015:118": {
        "doc_sections": ["talouden", "tunnusluvut", "vuosikate"],
        "edge_type": "RISK_FLAG",
    },
    # Kirjanpitolaki 3:2 (liitetiedot) → Liitetiedot
    "kirjanpitolaki_1336_1997:3:2": {
        "doc_sections": ["liitetiedot", "liitetiedot"],
        "edge_type": "REQUIRES_DISCLOSURE",
    },
    # Tilintarkastuslaki (kertomus) → Tilintarkastuskertomus
    "tilintarkastuslaki_1141_2015": {
        "doc_sections": ["tilintarkastuskertomus", "tilintarkastaja"],
        "edge_type": "EVIDENCED_BY",
    },
}


def load_document_index(chroma_dir: Path, collection_name: str = "lapua_2023"):
    """Load ChromaDB document index."""
    client = chromadb.PersistentClient(path=str(chroma_dir))
    collection = client.get_collection(collection_name)
    return client, collection


def find_document_evidence(
    query: str,
    collection,
    model: SentenceTransformer,
    k: int = 5,
    min_score: float = 0.30,
) -> list[dict]:
    """Find document nodes matching a query."""
    embedding = model.encode([query], normalize_embeddings=True)[0].tolist()
    
    results = collection.query(
        query_embeddings=[embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    
    hits = []
    for i, doc_id in enumerate(results["ids"][0]):
        # ChromaDB returns distance, convert to similarity
        distance = results["distances"][0][i]
        score = 1 - distance  # Cosine similarity
        
        if score < min_score:
            continue
        
        hits.append({
            "doc_node_id": doc_id,
            "score": score,
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
        })
    
    return hits


def apply_mapping_rules(
    law_node_id: str,
    doc_hits: list[dict],
) -> list[MappingEdge]:
    """Apply deterministic mapping rules."""
    edges: list[MappingEdge] = []
    
    # Check if law node matches any rule
    for rule_pattern, rule_config in MAPPING_RULES.items():
        if rule_pattern in law_node_id:
            # Check if any doc hit matches expected sections
            for hit in doc_hits:
                doc_title = hit.get("metadata", {}).get("title", "").lower()
                doc_text = hit.get("text", "").lower()
                
                for expected_section in rule_config["doc_sections"]:
                    if expected_section in doc_title or expected_section in doc_text:
                        edges.append({
                            "law_node_id": law_node_id,
                            "doc_node_id": hit["doc_node_id"],
                            "edge_type": rule_config["edge_type"],
                            "score": hit["score"],
                            "evidence_text": hit["text"][:200],
                            "context": f"Rule match: {rule_pattern} → {expected_section}",
                        })
                        break
    
    return edges


def map_law_to_document(
    law_hit: dict,
    collection,
    model: SentenceTransformer,
    k: int = 5,
) -> EvidenceBundle:
    """
    Map a legal hit to document evidence.
    
    Args:
        law_hit: Legal retrieval result with node_id, text, section_title
        collection: ChromaDB collection for document search
        model: Embedding model
        k: Number of document hits to retrieve
        
    Returns:
        EvidenceBundle with document nodes and mapping edges
    """
    # Build query from law hit
    query_parts = []
    if law_hit.get("section_title"):
        query_parts.append(law_hit["section_title"])
    if law_hit.get("text"):
        query_parts.append(law_hit["text"][:200])
    
    query = " ".join(query_parts)
    
    # Find document evidence
    doc_hits = find_document_evidence(query, collection, model, k)
    
    # Apply mapping rules
    law_node_id = law_hit.get("node_id", "")
    mapping_edges = apply_mapping_rules(law_node_id, doc_hits)
    
    # If no rule matches, create generic mappings based on score
    if not mapping_edges and doc_hits:
        for hit in doc_hits[:3]:
            mapping_edges.append({
                "law_node_id": law_node_id,
                "doc_node_id": hit["doc_node_id"],
                "edge_type": "EVIDENCED_BY",
                "score": hit["score"],
                "evidence_text": hit["text"][:200],
                "context": "Semantic similarity match",
            })
    
    return {
        "law_node_id": law_node_id,
        "law_section": law_hit.get("section_title", ""),
        "doc_nodes": doc_hits,
        "mapping_edges": mapping_edges,
    }


def interactive_mode(chroma_dir: Path) -> None:
    """Interactive mapping mode."""
    print("=" * 60)
    print("v9.2: Law↔Document Mapping (Interactive)")
    print("=" * 60)
    
    print("\nLoading document index...")
    client, collection = load_document_index(chroma_dir)
    
    print("Loading embedding model...")
    model = SentenceTransformer("BAAI/bge-m3")
    
    print("\nEnter queries to find document evidence.")
    print("Format: <law_section> | <query text>")
    print("Example: kuntalaki_410_2015:115 | toimintakertomus sisäinen valvonta")
    print("Type 'quit' to exit.\n")
    
    while True:
        try:
            user_input = input("Query> ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        
        if not user_input or user_input.lower() == "quit":
            break
        
        # Parse input
        if "|" in user_input:
            law_part, query_part = user_input.split("|", 1)
            law_node_id = law_part.strip()
            query = query_part.strip()
        else:
            law_node_id = ""
            query = user_input
        
        # Search documents
        doc_hits = find_document_evidence(query, collection, model, k=5)
        
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"Law: {law_node_id}")
        print(f"{'='*60}")
        
        if not doc_hits:
            print("No matching documents found.")
        else:
            for i, hit in enumerate(doc_hits):
                meta = hit["metadata"]
                print(f"\n[{i+1}] {hit['doc_node_id']} (score: {hit['score']:.3f})")
                print(f"    Type: {meta.get('node_type')}, Page: {meta.get('page_num')}")
                print(f"    Title: {meta.get('title', '')}")
                print(f"    Text: {hit['text'][:150]}...")
        
        # Apply mapping rules if law_node_id provided
        if law_node_id:
            edges = apply_mapping_rules(law_node_id, doc_hits)
            if edges:
                print(f"\n--- Mapping Edges ---")
                for edge in edges:
                    print(f"  {edge['edge_type']}: {edge['law_node_id']} → {edge['doc_node_id']}")
        
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Law↔Document Mapping Engine")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--doc-index", "-d", required=True, help="Path to document ChromaDB")
    parser.add_argument("--law-hits", "-l", help="Path to law hits JSON (batch mode)")
    parser.add_argument("--output", "-o", help="Output path for mappings (batch mode)")
    args = parser.parse_args()
    
    doc_index_path = Path(args.doc_index)
    
    if args.interactive:
        interactive_mode(doc_index_path)
    elif args.law_hits and args.output:
        # Batch mode
        print("Batch mode not yet implemented. Use --interactive for now.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

