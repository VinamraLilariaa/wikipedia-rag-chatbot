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
        self.store = ChromaStore()
        self.llm = LLMService()

    def ask(self, question: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        SHADOW-RAG PRODUCTION: High-Speed, Zero-Crash Retrieval.
        """
        start_time = time.time()
        question = question.strip()

        try:
            # 1. ACQUISITION: Directly reach Wikipedia
            article = self.wiki.get_article(question)
            title = article["title"]

            # 2. SHADOW-INDEXING: Fast RAM Chunking
            if not self.store.exists(title):
                self.store.add_article(title, article["content"])

            # 3. FUZZY RETRIEVAL: Find top chunks without heavy models
            chunks = self.store.get_all_chunks(title)
            # Use the Shadow Engine to find the most relevant 6 chunks
            top_contexts = self.embedder.get_similarity(question, chunks, limit=6)
            context_text = "\n\n".join(top_contexts)
            
            # 4. FINAL GROUNDING
            answer = self.llm.generate(
                question=question, 
                context=context_text,
                history=history
            )

            return {
                "answer": answer,
                "article": title,
                "wikipedia_url": article["url"],
                "sources": [title],
                "images": article["images"],
                "cache_hit": False,
                "response_time": round(time.time() - start_time, 2),
                "model": "Groq-Llama3-ShadowRAG",
                "spelling_corrected": False,
                "matched_query": title,
                "error": None
            }

        except Exception as e:
            logger.exception(f"Shadow-RAG Failure: {e}")
            return {
                "answer": f"I found the page for '{question}', but had trouble processing the details. Please try another specific question.",
                "article": "Process Error",
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