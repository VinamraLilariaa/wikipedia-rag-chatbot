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
        search_query = question

        # 1. BRAIN: Contextual Query Rewriting
        if history and len(history) > 0:
            history_text = "\n".join([f"{m['role']}: {m.get('text', m.get('data', {}).get('answer', ''))}" for m in history[-3:]])
            rewrite_prompt = (
                "You are an AI search optimizer. Identify the main subject being discussed.\n"
                "Rewrite the latest question as a standalone search query for Wikipedia.\n"
                "STRICT RULES:\n"
                "1. Always include the FULL NAME of the subject.\n"
                "2. NO 'List of' or 'Table of' unless asked.\n"
                "3. RETURN ONLY THE QUERY. NO CHATTER.\n\n"
                f"History:\n{history_text}\n\nLatest Question: {question}\n\nQuery:"
            )
            candidate = self.llm.simple_generate(rewrite_prompt).strip().strip('"').strip("'")
            # Clean up potential LLM chatter
            if "Query:" in candidate: candidate = candidate.split("Query:")[-1].strip()
            if candidate and len(candidate) > 2 and len(candidate.split()) < 10:
                search_query = candidate

        # 2. RETRIEVAL: Search and Index
        try:
            try:
                article, cache_hit = self._index_article(search_query)
            except Exception:
                # FALLBACK: If rewritten query fails, try original question
                logger.info(f"Retrying with original question: {question}")
                article, cache_hit = self._index_article(question)

            query_embedding = self.embedder.embed_query(question)
            
            # 3. SEARCH: High-resolution vector retrieval
            results = self.chroma.search(query_embedding, top_k=15)
            
            # Lead-Lock: Ensure intro chunks are present
            intro_chunks = [d for d, id in zip(results.get("documents", [[]])[0], results.get("ids", [[]])[0]) if "_0" in id or "_1" in id]
            retrieved_chunks = results["documents"][0]
            
            context_list = list(set(intro_chunks + retrieved_chunks))
            context = "\n\n".join(context_list)
            
            # 4. GENERATION: Final Answer
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