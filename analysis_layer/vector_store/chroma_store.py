"""
ChromaDB vector store implementation.

Provides a simple interface for storing and querying law documents.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings


class ChromaVectorStore:
    """ChromaDB-based vector store for legal documents."""

    def __init__(
        self,
        persist_directory: str | Path,
        collection_name: str = "kuntalaki",
    ) -> None:
        """Initialize ChromaDB client with persistence.

        Args:
            persist_directory: Directory to persist the database
            collection_name: Name of the collection
        """
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False),
        )

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """Add documents to the collection.

        Args:
            ids: Unique identifiers for each document
            documents: Text content of each document
            embeddings: Pre-computed embeddings
            metadatas: Metadata for each document
        """
        # ChromaDB requires metadata values to be str, int, float, or bool
        clean_metadatas = []
        for meta in metadatas:
            clean_meta = {}
            for k, v in meta.items():
                if isinstance(v, list):
                    clean_meta[k] = json.dumps(v)  # Serialize lists to JSON
                elif isinstance(v, (str, int, float, bool)):
                    clean_meta[k] = v
                else:
                    clean_meta[k] = str(v)
            clean_metadatas.append(clean_meta)

        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=clean_metadatas,
        )

    def query(
        self,
        query_embedding: list[float],
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Query the collection for similar documents.

        Args:
            query_embedding: Query vector
            n_results: Number of results to return
            where: Optional metadata filter

        Returns:
            Query results with documents, distances, and metadata
        """
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

    def count(self) -> int:
        """Return the number of documents in the collection."""
        return self.collection.count()

    def delete_collection(self) -> None:
        """Delete the entire collection."""
        self.client.delete_collection(self.collection.name)

