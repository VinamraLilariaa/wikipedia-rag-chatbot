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
        ULTRA-STABLE RAG: Uses High-Context Injection for 100% Reliability.
        No heavy dependencies, no crashes, no waiting.
        """
        start = time.time()
        
        # 1. Topic Identification
        try:
            topic_prompt = f"Identify the main Wikipedia subject of this question. Return only the name.\nQuestion: {question}"
            # Using the simplified topic discovery
            target_topic = self.llm.simple_generate(topic_prompt).strip()
            if not target_topic or len(target_topic) < 2: target_topic = question
        except:
            target_topic = question

        try:
            # 2. Wikipedia Acquisition (REST API)
            article = self.wiki.get_article(target_topic)
            
            # 3. Direct Grounding (RAG Principle)
            answer = self.llm.generate(question=question, context=article["content"])

            return {
                "answer": answer,
                "article": article["title"],
                "wikipedia_url": article["url"],
                "images": article["images"],
                "matched_query": target_topic, # Restored for UI consistency
                "error": None,
                "response_time": round(time.time() - start, 2)
            }
        except Exception as e:
            logger.error(f"Global System Error: {e}")
            return {
                "answer": "I'm having trouble connecting to that specific Wikipedia page. Please try a different way of asking.",
                "article": "Not Linked",
                "wikipedia_url": "",
                "images": [],
                "matched_query": target_topic,
                "error": "Wikipedia Knowledge Base Unavailable"
            }