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
        # Deep check: see if the data is actually in the vector DB
        if self.chroma.exists(article["title"]):
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
            if "Query:" in candidate: candidate = candidate.split("Query:")[-1].strip()
            if candidate and len(candidate) > 2:
                search_query = candidate

        try:
            article, cache_hit = self._index_article(search_query)
            query_embedding = self.embedder.embed_query(question)
            
            # High-resolution retrieval
            results = self.chroma.search(query_embedding, top_k=15)
            
            # Lead-Lock: Always include the first few chunks (Intro) to ensure basic facts are present
            intro_chunks = [d for d, id in zip(results.get("documents", [[]])[0], results.get("ids", [[]])[0]) if "_0" in id or "_1" in id]
            retrieved_chunks = results["documents"][0]
            
            context_list = list(set(intro_chunks + retrieved_chunks))
            context = "\n\n".join(context_list)
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
            logger.error(traceback.format_exc())
            return {
                "answer": "I hit a snag while searching Wikipedia. Please try again.",
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