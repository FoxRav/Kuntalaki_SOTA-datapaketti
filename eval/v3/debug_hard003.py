"""Debug KL-HARD-003 to understand why 114 still wins over 113."""

import sys
sys.path.insert(0, "F:\\-DEV-\\22.Kuntalaki")

import json
from sentence_transformers import SentenceTransformer
from analysis_layer.vector_store.chroma_store import ChromaVectorStore
from analysis_layer.query_boost import apply_query_boost

model = SentenceTransformer("BAAI/bge-m3")
store = ChromaVectorStore("F:\\-DEV-\\22.Kuntalaki\\analysis_layer\\embeddings\\chroma_db")

query = "Yksittaisen kunnan tilinpaatoksen asiakirjat (ei konserni)"
print(f"Query: {query}\n")

embedding = model.encode([query], normalize_embeddings=True)[0]
results = store.query(embedding.tolist(), n_results=10)

hits = []
for doc, meta, dist in zip(
    results["documents"][0],
    results["metadatas"][0],
    results["distances"][0],
):
    anchors = meta.get("anchors", [])
    if isinstance(anchors, str):
        try:
            anchors = json.loads(anchors)
        except:
            anchors = []
    
    hits.append({
        "section_num": meta.get("section_id", ""),
        "moment": meta.get("moment", ""),
        "section_title": meta.get("section_title", ""),
        "node_id": meta.get("node_id", ""),
        "score": round(1 - dist, 4),
        "text": doc[:200],
        "anchors": anchors,
    })

print("=== BEFORE BOOST ===")
for h in hits[:5]:
    print(f"  {h['section_num']}:{h['moment']} score={h['score']:.4f} - {h['section_title'][:30]}")
    print(f"    anchors: {h['anchors']}")

# Apply boost
boosted = apply_query_boost(query, hits)

print("\n=== AFTER BOOST ===")
for h in boosted[:5]:
    boost = h.get('boost_applied', 0)
    print(f"  {h['section_num']}:{h['moment']} score={h['score']:.4f} boost={boost:+.4f} - {h['section_title'][:30]}")

