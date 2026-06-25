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
        
        # 1. Subject Locking
        context_prompt = (
            "Based on the history and question, what is the primary SUBJECT (person/entity)?\n"
            "History:\n" + ("\n".join([f"{m['role']}: {m['text'] if 'text' in m else ''}" for m in (history or [])[-5:]])) + "\n"
            f"Question: {question}\n\n"
            "Return ONLY the name."
        )
        primary_subject = self.llm.simple_generate(context_prompt).strip().strip('"').strip("'")
        search_query = primary_subject if len(primary_subject) > 2 else question

        try:
            # 2. Retrieval
            try:
                article, cache_hit = self._index_article(search_query)
            except Exception:
                article, cache_hit = self._index_article(question)

            query_embedding = self.embedder.embed_query(question)
            results = self.chroma.search(query_embedding, top_k=20) # Deep vision
            
            # 3. Memory Ordering (CRITICAL)
            # Find the intro chunks and put them at the TOP of the context
            all_chunks = []
            id_to_chunk = {id: d for d, id in zip(results.get("documents", [[]])[0], results.get("ids", [[]])[0])}
            
            # Sort IDs to find the beginning of the article
            sorted_ids = sorted(id_to_chunk.keys(), key=lambda x: int(x.split('_')[-1]) if '_' in x else 0)
            
            # Always take the first 3 chunks (Intro/Infobox) regardless of similarity
            intro_ids = [id for id in sorted_ids if int(id.split('_')[-1]) < 3]
            intro_chunks = [id_to_chunk[id] for id in intro_ids]
            
            # Take rest of the retrieved chunks
            retrieved_chunks = results["documents"][0]
            
            # Final ordered context: Intro FIRST, then relevant chunks
            context_list = intro_chunks + [c for c in retrieved_chunks if c not in intro_chunks]
            context = "\n\n".join(context_list)
            
            # 4. Generation
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
                "answer": "I hit a snag while searching Wikipedia. Please try a different question.",
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