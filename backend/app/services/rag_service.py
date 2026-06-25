import time
import re
import logging
from typing import List, Dict, Any

from backend.app.services.wikipedia_service import WikipediaService
from backend.app.services.chroma_store import ChromaStore
from backend.app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

# Pronouns that indicate a follow-up about the same subject
FOLLOW_UP_RE = re.compile(
    r'\b(he|she|they|it|his|her|their|its|him|this person|the player|'
    r'the politician|the actor|the cricketer|the same|the president|the minister)\b',
    re.IGNORECASE,
)


class RAGService:
    def __init__(self):
        self.wiki = WikipediaService()
        self.store = ChromaStore()
        self.llm = LLMService()
        self._last_title: str = None   # Session memory

    def ask(self, question: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        start = time.time()
        question = question.strip()

        # ── 1. TOPIC RESOLUTION ──────────────────────────────────────────────
        # If the question is a pronoun follow-up, reuse the last article
        search_query = question
        if self._last_title and FOLLOW_UP_RE.search(question):
            search_query = self._last_title
            logger.info(f"Follow-up detected → reusing '{self._last_title}'")

        # ── 2. WIKIPEDIA RETRIEVAL ───────────────────────────────────────────
        try:
            article = self.wiki.get_article(search_query)
        except Exception as wiki_err:
            logger.exception("Wikipedia fetch failed")
            return self._error_response(question, start, str(wiki_err))

        title = article["title"]
        self._last_title = title

        # ── 3. CHUNKING & INDEXING ───────────────────────────────────────────
        try:
            if not self.store.article_exists(title):
                self.store.add_documents(title, article["content"])
        except Exception as idx_err:
            logger.warning(f"Indexing failed (non-fatal): {idx_err}")

        # ── 4. RETRIEVAL ─────────────────────────────────────────────────────
        try:
            chunks = self.store.get_article_chunks(title)
            top_chunks = self.store.search(question, chunks, top_k=6)
            context = "\n\n".join(top_chunks)
        except Exception:
            context = ""

        # Fallback: use article head directly if retrieval produced too little
        if len(context) < 200:
            context = article["content"][:7000]

        # ── 5. GENERATION ────────────────────────────────────────────────────
        try:
            answer = self.llm.generate(question=question, context=context)
        except Exception as llm_err:
            logger.exception("LLM generation failed")
            # Graceful degradation: return the Wikipedia extract directly
            answer = (
                f"(AI synthesis unavailable) Here is the Wikipedia extract:\n\n"
                f"{article['content'][:1500]}"
            )

        # ── 6. RESPONSE ──────────────────────────────────────────────────────
        return {
            "answer": answer,
            "article": title,
            "wikipedia_url": article["url"],
            "sources": [title],
            "images": article["images"],
            "cache_hit": False,
            "response_time": round(time.time() - start, 2),
            "model": "Groq-Llama3",
            "spelling_corrected": False,
            "matched_query": title,
        }

    # ── helpers ──────────────────────────────────────────────────────────────

    def _error_response(self, question: str, start: float, error: str) -> Dict[str, Any]:
        return {
            "answer": (
                f"I couldn't find a Wikipedia article for '{question}'. "
                "Please check the spelling or try a more specific name."
            ),
            "article": "Not Found",
            "wikipedia_url": "",
            "sources": [],
            "images": [],
            "cache_hit": False,
            "response_time": round(time.time() - start, 2),
            "model": "error",
            "spelling_corrected": False,
            "matched_query": question,
        }