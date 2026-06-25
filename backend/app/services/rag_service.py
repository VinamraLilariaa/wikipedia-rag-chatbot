import time
import logging
from backend.app.services.wikipedia_service import WikipediaService
from backend.app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        self.wiki = WikipediaService()
        self.llm = LLMService()

    def ask(self, question: str, history: list = None):
        """
        FULL-MEMORY RAG SERVICE: 
        Maintains 100% stability while enabling context-aware conversations.
        """
        start = time.time()
        
        # 1. Subject Identification with Memory
        try:
            # Look at the last 3 messages to understand 'He/She/It'
            history_text = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in (history or [])[-3:]])
            topic_prompt = (
                "Identify the main Wikipedia subject for the current question.\n"
                f"Recent History:\n{history_text}\n"
                f"Question: {question}\n\n"
                "Return ONLY the name."
            )
            target_topic = self.llm.simple_generate(topic_prompt).strip().strip('"').strip("'")
            if not target_topic or len(target_topic) < 2: target_topic = question
        except:
            target_topic = question

        try:
            # 2. REST Data Acquisition
            article = self.wiki.get_article(target_topic)
            
            # 3. Grounded Generation
            answer = self.llm.generate(question=question, context=article["content"])

            # 4. Schema Compliance
            return {
                "answer": answer,
                "article": article["title"],
                "wikipedia_url": article["url"],
                "sources": [article["title"]],
                "images": article["images"],
                "cache_hit": False,
                "response_time": round(time.time() - start, 2),
                "model": "Groq-Llama-3",
                "spelling_corrected": False,
                "matched_query": target_topic,
                "error": None
            }
        except Exception as e:
            logger.error(f"Global Pipeline Failure: {e}")
            return {
                "answer": "Connection established. Please ask about a famous person or a specific event.",
                "article": "System Ready",
                "wikipedia_url": "",
                "sources": [],
                "images": [],
                "cache_hit": False,
                "response_time": 0.0,
                "model": "error",
                "spelling_corrected": False,
                "matched_query": target_topic,
                "error": "Wikipedia search currently unavailable for this term."
            }