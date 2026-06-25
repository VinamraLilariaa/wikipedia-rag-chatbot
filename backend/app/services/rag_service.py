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
        FAIL-SAFE RAG: Guaranteed intelligence even on complex articles.
        """
        start_time = time.time()
        question = question.strip()

        try:
            # 1. ACQUISITION: Direct Wikipedia Search
            article = self.wiki.get_article(question)
            title = article["title"]
            
            # 2. REDUNDANT EXTRACTION: Get multiple layers of context
            raw_content = article.get("content", "")
            summary = article.get("summary", "") # Fast-path summary
            
            # 3. CONTEXT ASSEMBLY (With Auto-Fallback)
            context_text = ""
            try:
                if not self.store.exists(title):
                    self.store.add_article(title, raw_content[:15000])
                
                chunks = self.store.get_all_chunks(title)
                if chunks:
                    top_contexts = self.embedder.get_similarity(question, chunks, limit=5)
                    context_text = "\n\n".join(top_contexts)
            except:
                logger.warning("Shadow-Search failed, using summary fallback.")
                context_text = ""

            # If search is empty or low quality, use the deep summary directly
            if len(context_text) < 100:
                context_text = (summary + "\n\n" + raw_content)[:8000]

            # 4. FINAL GROUNDING: LLM synthesizes the answer
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
                "model": "Groq-Llama3-Resilient",
                "spelling_corrected": False,
                "matched_query": title,
                "error": None
            }

        except Exception as e:
            logger.exception(f"Resilient RAG Failure: {e}")
            return {
                "answer": "The wisdom of Wikipedia is currently being updated. Please try a different question.",
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