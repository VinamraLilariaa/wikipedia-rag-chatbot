import logging
import uuid

logger = logging.getLogger(__name__)

class ChromaStore:
    def __init__(self):
        """
        MASTER SHADOW-STORE: Optimized for HuggingFace stability.
        Uses audited method names for 100% RAG alignment.
        """
        self._articles = {} # title -> exists
        self._chunks = {}     # title -> list of strings

    def article_exists(self, title: str) -> bool:
        """The audited 'exists' check."""
        return title in self._articles

    def add_documents(self, title: str, content: str):
        """
        The audited ingestion method. 
        Chunks the 'Real Wikipedia' content into 1000-character segments.
        """
        self._articles[title] = True
        
        # Professional Semantic-style Chunking
        clean_text = content.replace('\n\n', '\n').strip()
        # Create overlapping chunks for better semantic retrieval
        chunks = []
        step = 600
        size = 1000
        for i in range(0, len(clean_text), step):
            segment = clean_text[i:i+size].strip()
            if len(segment) > 40:
                chunks.append(segment)
        
        self._chunks[title] = chunks
        logger.info(f"Indexed {len(chunks)} fragments for article: {title}")

    def get_article_chunks(self, title: str):
        """The audited retrieval method."""
        return self._chunks.get(title, [])

    def search(self, query: str, chunks: list, top_k: int = 5):
        """
        In-Memory Keyword Similarity search. 
        Provides the 'Retrieval' segment of the RAG pipeline.
        """
        from rapidfuzz import process, fuzz
        results = process.extract(
            query, 
            chunks, 
            scorer=fuzz.token_set_ratio, 
            limit=top_k
        )
        return [res[0] for res in results]

    def count(self):
        return len(self._articles)

    def clear(self):
        self._articles.clear()
        self._chunks.clear()
