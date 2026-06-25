import time
import logging
import traceback

from backend.app.services.wikipedia_service import WikipediaService
from backend.app.services.embedding_service import EmbeddingService
from backend.app.services.chroma_store import ChromaStore
from backend.app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        self.wiki = WikipediaService()
        self.embedder = EmbeddingService()
        self.chroma = ChromaStore()
        self.llm = LLMService()

    def ask(self, question: str, history: list = None):
        """
        OFFICIAL REST-RAG PIPELINE: 
        1. Discover Subject
        2. Fetch via REST API
        3. Index into ChromaDB
        4. Vector Retrieval
        5. Grounded Generation
        """
        start = time.time()
        
        # 1. Topic Identification
        try:
            topic_prompt = f"Identify the main Wikipedia subject of this question. Return only the name.\nQuestion: {question}"
            target_topic = self.llm.simple_generate(topic_prompt).strip()
            if not target_topic: target_topic = question
        except:
            target_topic = question

        try:
            # 2. REST API Data Acquisition
            article = self.wiki.get_article(target_topic)
            title = article["title"]
            
            # 3. RAG CORE: Vector Indexing & Search
            try:
                if not self.chroma.exists(title):
                    # Indexing the REST content (Summary + Body)
                    self.chroma.add_article(title, article["content"])
                
                query_embedding = self.embedder.embed_query(question)
                results = self.chroma.search(query_embedding, top_k=10)
                context = "\n\n".join(results.get("documents", [[]])[0])
                
                # Double-check: ensure the summary is always in context for accuracy
                if article["summary"] not in context:
                    context = f"SUMMARY: {article['summary']}\n\n" + context
            except Exception as vdb_err:
                logger.error(f"VDB Fallback triggered: {vdb_err}")
                context = article["content"][:30000]

            # 4. Final Answer Generation
            answer = self.llm.generate(question=question, context=context)

            return {
                "answer": answer,
                "article": title,
                "wikipedia_url": article["url"],
                "sources": [title],
                "images": article["images"],
                "matched_query": target_topic,
                "error": None
            }
        except Exception as e:
            logger.error(f"REST-RAG Critical Error: {e}")
            return {
                "answer": "I'm having trouble connecting to Wikipedia sources. Please try again in 30 seconds.",
                "article": "Connection Issue",
                "wikipedia_url": "",
                "sources": [],
                "images": [],
                "matched_query": target_topic,
                "error": "Wikipedia REST API Unavailable"
            }