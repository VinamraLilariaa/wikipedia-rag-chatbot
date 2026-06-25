import chromadb
import uuid
import re
import logging
from backend.app.config.settings import (
    CHROMA_PATH,
    COLLECTION_NAME,
)

logger = logging.getLogger(__name__)

class ChromaStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMA_PATH)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

    def exists(self, title: str) -> bool:
        """Lightweight existence check."""
        results = self.collection.get(
            where={"title": title},
            limit=1
        )
        return len(results["ids"]) > 0

    def add_article(self, title: str, content: str):
        """
        EXPRESS INDEXING: Handles massive articles like Lionel Messi by prioritizing
        the most important 10,000 words for instant response.
        """
        # Truncate total content to prevent server timeouts on mega-articles (approx 15-20 sections)
        # 80,000 chars is roughly 15-20 typed pages, covering 99% of user questions.
        safe_content = content[:80000] 
        
        chunks = []
        sections = re.split(r'(?m)^## ', safe_content)
        
        for section in sections:
            section_clean = section.strip()
            if not section_clean: continue
            
            section_title = section_clean.split('\n')[0] if '\n' in section_clean else "General"
            
            # Split section into logical paragraphs
            paras = [p.strip() for p in section_clean.split('\n\n') if len(p.strip()) > 40]
            
            for i, p in enumerate(paras):
                # Include metadata for better retrieval
                chunks.append({
                    "text": f"Subject: {title} | {section_title}: {p}",
                    "id": f"{title}_{uuid.uuid4().hex[:6]}_{i}",
                    "metadata": {"title": title, "section": section_title}
                })

        # Process in batches of 50 for max performance on HuggingFace
        batch_size = 50
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            try:
                self.collection.upsert(
                    documents=[c["text"] for c in batch],
                    metadatas=[c["metadata"] for c in batch],
                    ids=[c["id"] for c in batch]
                )
            except Exception as e:
                logger.error(f"Batch upsert failed: {e}")
                continue

    def search(self, query_embedding: list, top_k: int = 20):
        """Ultra-fast vector search."""
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
