import time
import re
import logging
from typing import List, Dict, Any

from backend.app.services.wikipedia_service import WikipediaService
from backend.app.services.chroma_store import ChromaStore
from backend.app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

# Pronouns that signal a follow-up question about the same topic
FOLLOW_UP_SIGNALS = re.compile(
    r'\b(he|she|they|it|his|her|their|its|him|this person|the player|the politician|the actor|the same)\b',
    re.IGNORECASE
)

class RAGService:
    def __init__(self):
        self.wiki = WikipediaService()
        self.store = ChromaStore()
        self.llm = LLMService()
        self._last_title = None  # Session memory: last successfully retrieved article

    def ask(self, question: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        start_time = time.time()
        question = question.strip()

        try:
            # 1. SMART TOPIC RESOLUTION
            # If the question contains pronouns and we have a previous article, reuse it
            search_query = question
            if self._last_title and FOLLOW_UP_SIGNALS.search(question):
                search_query = self._last_title
                logger.info(f"Follow-up detected. Reusing article: '{self._last_title}'")

            # 2. RETRIEVE: Fetch full Wikipedia article
            article = self.wiki.get_article(search_query)
            title = article["title"]
            self._last_title = title  # Remember for follow-ups

            # 3. INDEX: Chunk and store if not already done
            if not self.store.article_exists(title):
                self.store.add_documents(title, article["content"])

            # 4. SEARCH: Find most relevant chunks
            chunks = self.store.get_article_chunks(title)
            top_chunks = self.store.search(question, chunks, top_k=6)
            context = "\n\n".join(top_chunks)

            # Fallback if search returns too little
            if len(context) < 200:
                context = article["content"][:8000]

            # 5. GENERATE: Grounded answer from LLM
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