import time
import logging
import traceback
import re

from backend.app.services.wikipedia_service import WikipediaService
from backend.app.services.cache_service import CacheService
from backend.app.services.embedding_service import EmbeddingService
from backend.app.services.chroma_store import ChromaStore
from backend.app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        self.wiki = WikipediaService()
        self.cache = CacheService()
        self.embedder = EmbeddingService()
        self.chroma = ChromaStore()
        self.llm = LLMService()

    def _index_article(self, query: str):
        try:
            article = self.wiki.get_article(query)
            if self.chroma.exists(article["title"]):
                return article, True
            
            self.chroma.add_article(article["title"], article["content"])
            self.cache.add(article["title"], article["url"], 0)
            return article, False
        except Exception as e:
            logger.warning(f"Indexing failed for '{query}': {e}")
            raise

    def ask(self, question: str, history: list = None):
        start = time.time()
        
        # 1. Subject Extraction & Locking
        # Identify the primary subject from the ENTIRE conversation to prevent "Millennials" drift
        context_prompt = (
            "Based on this conversation history and the latest question, what is the single most likely SUBJECT (person or entity) being discussed?\n"
            "History:\n" + ("\n".join([f"{m['role']}: {m['text'] if 'text' in m else ''}" for m in (history or [])[-5:]])) + "\n"
            f"Question: {question}\n\n"
            "Return ONLY the name of the subject. NO OTHER TEXT."
        )
        primary_subject = self.llm.simple_generate(context_prompt).strip().strip('"').strip("'")
        
        # If the AI identified a clear subject, use it for the search
        search_query = primary_subject if len(primary_subject) > 2 else question

        # 2. Retrieval with Fallback
        try:
            try:
                article, cache_hit = self._index_article(search_query)
                # Final Sanity Check: If the article title is wildly different from our subject, try once more with the original question
                if len(primary_subject) > 3 and primary_subject.lower() not in article["title"].lower() and article["title"].lower() not in primary_subject.lower():
                    logger.warning(f"Suspected mismatch: Subject '{primary_subject}' vs Article '{article['title']}'. Retrying...")
                    article, cache_hit = self._index_article(question)
            except Exception:
                article, cache_hit = self._index_article(question)

            # 3. Context & Generation
            query_embedding = self.embedder.embed_query(question)
            results = self.chroma.search(query_embedding, top_k=15)
            
            intro_chunks = [d for d, id in zip(results.get("documents", [[]])[0], results.get("ids", [[]])[0]) if "_0" in id or "_1" in id]
            retrieved_chunks = results["documents"][0]
            context = "\n\n".join(list(set(intro_chunks + retrieved_chunks)))
            
            answer = self.llm.generate(question=question, context=context)

            return {
                "answer": answer,
                "article": article["title"],
                "wikipedia_url": article["url"],
                "sources": [],
                "images": article["images"],
                "matched_query": search_query,
                "cache_hit": cache_hit,
                "response_time": round(time.time() - start, 2),
                "model": "Groq Llama-3",
                "spelling_corrected": article.get("spelling_corrected", False)
            }
        except Exception as e:
            logger.error(f"RAG Error: {e}")
            return {
                "answer": "I hit a snag while searching Wikipedia. Please try a slightly different question.",
                "article": "Error",
                "wikipedia_url": "",
                "sources": [],
                "images": [],
                "matched_query": search_query,
                "cache_hit": False,
                "response_time": 0,
                "model": "error",
                "spelling_corrected": False
            }