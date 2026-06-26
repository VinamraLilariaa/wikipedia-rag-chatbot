import time
import re
import logging
from typing import List, Dict, Any

from backend.app.services.wikipedia_service import WikipediaService
from backend.app.services.chroma_store import ChromaStore
from backend.app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

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
        self._last_title: str = None

    def ask(self, question: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        start = time.time()
        question = question.strip()

        # ── 1. TOPIC RESOLUTION ──────────────────────────────────────────
        search_query = question
        if self._last_title and FOLLOW_UP_RE.search(question):
            search_query = self._last_title
            logger.info(f"Follow-up detected → reusing '{self._last_title}'")

        # ── 2. WIKIPEDIA RETRIEVAL ───────────────────────────────────────
        try:
            article = self.wiki.get_article(search_query)
        except Exception as wiki_err:
            logger.exception("Wikipedia fetch failed")
            return self._error_response(question, start, str(wiki_err))

        title = article["title"]
        self._last_title = title
        content = article["content"]

        # ── 3. SMART CONTEXT ASSEMBLY ────────────────────────────────────
        # Strategy: for short articles (<15k chars), send the WHOLE thing.
        # For long articles, use chunked retrieval + fallback to head.
        context = self._build_context(question, title, content)

        # ── 4. LLM GENERATION ────────────────────────────────────────────
        try:
            answer = self.llm.generate(question=question, context=context)
        except Exception as llm_err:
            logger.exception("LLM generation failed")
            # Graceful degradation — return Wikipedia extract directly
            answer = f"Wikipedia extract: {content[:1500]}"

        return {
            "answer": answer,
            "article": title,
            "wikipedia_url": article["url"],
            "sources": [title],
            "images": article["images"],
            "cache_hit": self.store.article_exists(title),
            "response_time": round(time.time() - start, 2),
            "model": "Groq-Llama3",
            "spelling_corrected": False,
            "matched_query": title,
        }

    def _build_context(self, question: str, title: str, content: str) -> str:
        """
        Build the best possible context for the LLM.
        - Short articles  (<12k chars): send the entire article
        - Long articles   (>=12k chars): retrieve top chunks + fallback
        """
        # Index if not already done
        try:
            if not self.store.article_exists(title):
                self.store.add_documents(title, content)
        except Exception as e:
            logger.warning(f"Indexing failed (non-fatal): {e}")

        # Short article — send everything, no information loss
        if len(content) <= 12000:
            return content

        # Long article — try chunk retrieval first
        try:
            chunks = self.store.get_article_chunks(title)
            top   = self.store.search(question, chunks, top_k=8)
            ctx   = "\n\n".join(top)
            if len(ctx) >= 300:
                # Also prepend the first 1500 chars (article intro always relevant)
                intro = content[:1500]
                return f"{intro}\n\n---Retrieved Sections---\n\n{ctx}"
        except Exception as e:
            logger.warning(f"Chunk retrieval failed: {e}")

        # Final fallback — first 8000 chars of article
        return content[:8000]

    def _error_response(self, question: str, start: float, error: str) -> Dict[str, Any]:
        return {
            "answer": (
                f"I couldn't retrieve a Wikipedia article for '{question}'. "
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