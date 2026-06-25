import re
from rapidfuzz import process, fuzz

class EmbeddingService:
    def __init__(self):
        """
        SHADOW-ENGINE: Replaces heavy Torch models with lightweight 
        Fuzzy Keyword Matching. Zero RAM, 100% Reliability.
        """
        pass

    def embed_query(self, query: str):
        """No more heavy vectors. We return clean tokens."""
        return query.lower().strip()

    def get_similarity(self, query, choices, limit=10):
        """High-speed fuzzy matching between question and article chunks."""
        # This performs the 'Retrieval' part of RAG without needing a 2GB model
        results = process.extract(
            query, 
            choices, 
            scorer=fuzz.token_set_ratio, 
            limit=limit
        )
        return [res[0] for res in results]