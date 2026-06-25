import time
import logging
from typing import List, Dict, Any

from backend.app.services.wikipedia_service import WikipediaService
from backend.app.services.chroma_store import ChromaStore
from backend.app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        self.wiki = WikipediaService()
        self.store = ChromaStore()
        self.llm = LLMService()

    def ask(self, question: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        start_time = time.time()
        question = question.strip()

        try:
            # 1. RETRIEVE: Fetch full Wikipedia article
            article = self.wiki.get_article(question)
            title = article["title"]
            content = article["content"]

            # 2. INDEX: Chunk and store if not already done
            if not self.store.article_exists(title):
                self.store.add_documents(title, content)

            # 3. SEARCH: Find most relevant chunks via fuzzy matching
            chunks = self.store.get_article_chunks(title)
            top_chunks = self.store.search(question, chunks, top_k=6)
            context = "\n\n".join(top_chunks)

            # Fallback: if search returns too little, use article head directly
            if len(context) < 200:
                context = content[:8000]

            # 4. GENERATE: LLM synthesizes grounded answer
            answer = self.llm.generate(
                question=question,
                context=context,
                history=history,
            )

            return {
                "answer": answer,
                "article": title,
                "wikipedia_url": article["url"],
                "sources": [title],
                "images": article["images"],
                "cache_hit": False,
                "response_time": round(time.time() - start_time, 2),
                "model": "Groq-Llama3",
                "spelling_corrected": False,
                "matched_query": title,
                "error": None,
            }

        except Exception as e:
            logger.exception("RAG pipeline failure")
            return {
                "answer": f"Could not find or process a Wikipedia article for '{question}'. Please try rephrasing.",
                "article": "Not Found",
                "wikipedia_url": "",
                "sources": [],
                "images": [],
                "cache_hit": False,
                "response_time": round(time.time() - start_time, 2),
                "model": "error",
                "spelling_corrected": False,
                "matched_query": question,
                "error": str(e),
            }