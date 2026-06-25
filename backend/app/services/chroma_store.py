import chromadb
import logging
from backend.app.config.settings import (
    CHROMA_PATH,
    COLLECTION_NAME,
)

logger = logging.getLogger(__name__)

class ChromaStore:
    def __init__(self):
        # Create persistent client
        self.client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME
        )

    def add_article(self, title: str, content: str):
        """
        Chunk content and add to ChromaDB with ultra-robust splitting.
        """
        if not content:
            logger.warning(f"Attempted to add empty content for '{title}'")
            return

        # Split by various possible separators to ensure we don't miss anything
        import re
        # Split by double newlines OR headers
        raw_chunks = re.split(r'\n\n|(?=##)', content)
        
        # Cleanup and filter
        paragraphs = []
        for p in raw_chunks:
            p = p.strip()
            if not p: continue
            # If a chunk is way too long, split it further by single newlines
            if len(p) > 2000:
                sub_chunks = [sc.strip() for sc in p.split('\n') if len(sc.strip()) > 30]
                paragraphs.extend(sub_chunks)
            elif len(p) > 10: # Very low threshold to capture all data
                paragraphs.append(p)
        
        if not paragraphs:
            return

        ids = [f"{title}_{i}" for i in range(len(paragraphs))]
        metadatas = [{"title": title} for _ in range(len(paragraphs))]
        
        # Upsert to avoid duplications while ensuring fresh data
        self.collection.upsert(
            documents=paragraphs,
            ids=ids,
            metadatas=metadatas
        )
        logger.info(f"Indexed {len(paragraphs)} chunks for '{title}'")

    def search(self, query_embedding, top_k: int = 15):
        """
        Search for most similar chunks.
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        # Ensure we always return something shaped correctly even if no results
        if not results or not results["documents"]:
            return {"documents": [[]], "ids": [[]]}
        return results

    def exists(self, title: str) -> bool:
        """Check if an article is already indexed in Chroma"""
        results = self.collection.get(
            where={"title": title},
            limit=1
        )
        return len(results.get("ids", [])) > 0
