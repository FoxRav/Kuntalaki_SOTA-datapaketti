"""Find where §113 ranks for KL-HARD-003 query."""
import sys
sys.path.insert(0, "F:\\-DEV-\\22.Kuntalaki")

from sentence_transformers import SentenceTransformer
from analysis_layer.vector_store.chroma_store import ChromaVectorStore

model = SentenceTransformer("BAAI/bge-m3")
store = ChromaVectorStore("F:\\-DEV-\\22.Kuntalaki\\analysis_layer\\embeddings\\chroma_db")

query = "Yksittaisen kunnan tilinpaatoksen asiakirjat ei konserni"
print(f"Query: {query}\n")

embedding = model.encode([query], normalize_embeddings=True)[0]
results = store.query(embedding.tolist(), n_results=100)

print("=== 113 sections in results ===")
for i, (meta, dist) in enumerate(zip(results["metadatas"][0], results["distances"][0])):
    if meta.get("section_id") == "113":
        print(f"Rank {i+1}: 113:{meta['moment']} score={1-dist:.4f}")

