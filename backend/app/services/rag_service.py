import time
import logging
import traceback

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
        article = self.wiki.get_article(query)
        if self.cache.exists(article["title"]):
            return article, True
        
        self.chroma.add_article(article["title"], article["content"])
        self.cache.add(article["title"], article["url"], 0)
        return article, False

    def ask(self, question: str, history: list = None):
        start = time.time()
        search_query = question

        if history and len(history) > 0:
            history_text = "\n".join([f"{m['role']}: {m.get('text', m.get('data', {}).get('answer', ''))}" for m in history[-3:]])
            rewrite_prompt = (
                "You are a search query generator. Based on the history, identify the subject and rewrite the latest question as a standalone search query.\n"
                "STRICT RULES:\n"
                "1. Replace pronouns with the subject's full name.\n"
                "2. RETURN ONLY THE QUERY. NO CHATTER. NO QUOTES.\n\n"
                f"History:\n{history_text}\n\nLatest Question: {question}\n\nQuery:"
            )
            candidate = self.llm.simple_generate(rewrite_prompt).strip().strip('"').strip("'")
            # Filter out any AI "yapping" if it happens
            if "Query:" in candidate: candidate = candidate.split("Query:")[-1].strip()
            if candidate and len(candidate) > 2:
                search_query = candidate

        try:
            article, cache_hit = self._index_article(search_query)
            query_embedding = self.embedder.embed_query(question)
            
            # Deeper retrieval for better fact-finding
            results = self.chroma.search(query_embedding, top_k=10)
            
            context = "\n\n".join(results["documents"][0])
            answer = self.llm.generate(question=question, context=context)

            return {
                "answer": answer,
                "article": article["title"],
                "wikipedia_url": article["url"],
                "sources": [], # Required by schema
                "images": article["images"],
                "matched_query": search_query,
                "cache_hit": cache_hit,
                "response_time": round(time.time() - start, 2),
                "model": "Groq Llama-3", # Required by schema
                "spelling_corrected": article.get("spelling_corrected", False)
            }
        except Exception as e:
            logger.error(f"RAG Error: {e}")
            return {"answer": "I'm sorry, I couldn't process that. Please try again.", "error": str(e)}