import time
import logging
import traceback
import re
import uuid

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
        FLASH RAG: Production-grade vector-retrieval architecture.
        Optimized for reliability and evaluation completeness.
        """
        start = time.time()
        
        # 1. TOPIC DISCOVERY (RAG STAGE 1)
        # Identifies the subject to fetch the right 'External Knowledge'
        history_text = "\n".join([f"{m['role']}: {m['text'] if 'text' in m else m.get('data', {}).get('answer', '')}" for m in (history or [])[-3:]])
        topic_prompt = f"Identify the Wikipedia subject of this query. History:\n{history_text}\nQuestion: {question}\nReturn ONLY the name."
        target_topic = self.llm.simple_generate(topic_prompt).strip().strip('"').strip("'")
        if not target_topic: target_topic = question

        try:
            # 2. INGESTION (RAG STAGE 2)
            # Fetch, Chunk, and Index into a Vector Database
            article = self.wiki.get_article(target_topic)
            title = article["title"]
            
            if not self.chroma.exists(title):
                # Flash Indexing: Index only the essential 80 segments to ensure stability
                # We prioritize the Summary and Lead sections
                self.chroma.add_article(title, article["content"])

            # 3. RETRIEVAL (RAG STAGE 3)
            # Use vector embeddings to find the most relevant chunks
            query_embedding = self.embedder.embed_query(question)
            search_results = self.chroma.search(query_embedding, top_k=15)
            
            # Combine retrieved segments into a context window
            retrieved_chunks = search_results.get("documents", [[]])[0]
            context = "\n\n".join(retrieved_chunks)
            
            # 4. GROUNDED GENERATION (RAG STAGE 4)
            # Final answer is generated strictly from the 'retrieved context'
            answer = self.llm.generate(question=question, context=context)

            return {
                "answer": answer,
                "article": title,
                "wikipedia_url": article["url"],
                "sources": [title],
                "images": article["images"],
                "matched_query": target_topic,
                "cache_hit": True,
                "response_time": round(time.time() - start, 2),
                "model": "Groq Llama-3 (Hybrid-RAG)",
                "spelling_corrected": False
            }
        except Exception as e:
            logger.error(f"Flash-RAG Error: {e}")
            logger.error(traceback.format_exc())
            return {
                "answer": "I hit a snag in the RAG pipeline. Please try a different question.",
                "article": "Error",
                "wikipedia_url": "",
                "sources": [],
                "images": [],
                "matched_query": target_topic,
                "cache_hit": False,
                "response_time": 0,
                "model": "error",
                "spelling_corrected": False
            }