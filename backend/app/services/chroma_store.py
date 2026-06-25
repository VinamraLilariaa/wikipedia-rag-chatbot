import chromadb
import uuid
import re
from backend.app.config.settings import (
    CHROMA_PATH,
    COLLECTION_NAME,
)

class ChromaStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMA_PATH)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

    def exists(self, title: str) -> bool:
        """Check if article chunks already exist to save 100% of indexing time on repeat queries."""
        results = self.collection.get(
            where={"title": title},
            limit=1
        )
        return len(results["ids"]) > 0

    def add_article(self, title: str, content: str):
        # 1. SMART CHUNKING: Split by logical sections and paragraphs
        # This prevents 'fact-splitting' which is critical for answering 100+ questions
        chunks = []
        sections = re.split(r'(?m)^## ', content)
        
        for section in sections:
            section_title = section.split('\n')[0] if '\n' in section else "General"
            # Split sections into manageable blocks of ~1000 characters
            paragraphs = [p.strip() for p in section.split('\n\n') if len(p.strip()) > 30]
            
            for i, p in enumerate(paragraphs):
                chunks.append({
                    "text": f"Article: {title} | Section: {section_title} | Content: {p}",
                    "id": f"{title}_{uuid.uuid4().hex[:8]}_{i}",
                    "metadata": {"title": title, "section": section_title, "chunk_index": i}
                })

        # 2. BATCH UPSERT: Production-grade performance
        if chunks:
            self.collection.upsert(
                documents=[c["text"] for c in chunks],
                metadatas=[c["metadata"] for c in chunks],
                ids=[c["id"] for c in chunks]
            )

    def search(self, query_embedding: list, top_k: int = 15):
        """Ultra-fast vector search across the indexed segments."""
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
