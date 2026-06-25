import time
import logging
from typing import List, Dict, Any

from backend.app.services.wikipedia_service import WikipediaService
from backend.app.services.embedding_service import EmbeddingService
from backend.app.services.chroma_store import ChromaStore
from backend.app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        self.wiki = WikipediaService()
        self.embedder = EmbeddingService()
        self.chroma = ChromaStore()
        self.llm = LLMService()
        self._cache = {}

    def ask(self, question: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        MASTER PRODUCTION RAG: Simplified, Grounded, and Reliable.
        Flow: Question -> Search -> Chunk -> Embed -> Retrieve -> Generate.
        """
        start_time = time.time()
        question = question.strip()

        try:
            # 1. ACQUISITION: Direct Wikipedia Search
            # No LLM-preprocessing. We use Wikipedia's own powerful search engine.
            article = self.wiki.get_article(question)
            title = article["title"]

            # 2. SEMANTIC INDEXING: Chunk and store in-memory (RAM-speed)
            # We only index if it's a new article to keep performance high.
            if not self.chroma.exists(title):
                self.chroma.add_article(title, article["content"])

            # 3. CONTEXTUAL RETRIEVAL: Find the most relevant segments
            query_embedding = self.embedder.embed_query(question)
            search_results = self.chroma.search(query_embedding, top_k=10)
            
            # Extract top segments for the LLM
            contexts = search_results.get("documents", [[]])[0]
            context_text = "\n\n".join(contexts)
            
            # 4. FINAL GROUNDING: LLM synthesizes the answer from the chunks
            answer = self.llm.generate(
                question=question, 
                context=context_text,
                history=history
            )

            # 5. RESPONSE: Full schema compliance with confidence
            return {
                "answer": answer,
                "article": title,
                "wikipedia_url": article["url"],
                "sources": [title],
                "images": article["images"],
                "cache_hit": title in self._cache,
                "response_time": round(time.time() - start_time, 2),
                "model": "Groq-Llama3-Grounded",
                "spelling_corrected": False,
                "matched_query": title,
                "error": None
            }

        except Exception as e:
            logger.exception(f"RAG Failure: {e}")
            # Explicit error return for the UI
            return {
                "answer": f"I had trouble finding or reading the Wikipedia page for '{question}'.",
                "article": "Search Failed",
                "wikipedia_url": "",
                "sources": [],
                "images": [],
                "cache_hit": False,
                "response_time": 0,
                "model": "error",
                "spelling_corrected": False,
                "matched_query": question,
                "error": str(e)
            }
        finally:
            # Simple in-session caching
            if 'title' in locals():
                self._cache[title] = True