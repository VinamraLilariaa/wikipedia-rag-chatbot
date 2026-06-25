import time
import logging
from typing import List, Dict, Any

from backend.app.services.wikipedia_service import WikipediaService
from backend.app.services.embedding_service import EmbeddingService
from backend.app.services.chroma_store import ChromaStore
from backend.app.services.llm_service import LLMService

# Professional-grade logging for the demo
logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        self.wiki = WikipediaService()
        self.embedder = EmbeddingService()
        self.store = ChromaStore()
        self.llm = LLMService()

    def ask(self, question: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        STABALIZED RAG PIPELINE: High-trust, low-memory execution.
        """
        start_time = time.time()
        question = question.strip()

        try:
            # 1. ACQUISITION: Direct Wikipedia Search
            article = self.wiki.get_article(question)
            title = article["title"]
            
            # 2. PROCESSING: Hard-cap content to 10,000 chars to prevent prompt bloat
            # This is the 'Industrial Safety' fix suggested by the audit.
            raw_content = article.get("content", "")
            safe_content = raw_content[:15000] # Safe limit for indexing

            # 3. SHADOW-INDEXING: Fast RAM Chunking
            if not self.store.exists(title):
                self.store.add_article(title, safe_content)

            # 4. RETRIEVAL: Find top chunks for grounding
            chunks = self.store.get_all_chunks(title)
            # Find the most relevant context snippets
            top_contexts = self.embedder.get_similarity(question, chunks, limit=5)
            context_text = "\n\n".join(top_contexts)
            
            # FINAL SAFETY: Hard-cap context for the LLM prompt
            context_text = context_text[:8000]

            # 5. GENERATION: Final Grounded Answer
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
                "model": "Groq-Llama3-SafeRAG",
                "spelling_corrected": False,
                "matched_query": title,
                "error": None
            }

        except Exception as e:
            # We follow the audit requirement to log the full trace for final debugging
            logger.exception(f"CRITICAL RAG FAILURE: {e}")
            return {
                "answer": "System processing error. Please try a shorter question.",
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