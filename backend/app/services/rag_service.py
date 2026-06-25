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

    def ask(self, question: str, history: list = None):
        start = time.time()
        
        # 1. TOPIC DISCOVERY: Identify the core Wikipedia article for this conversation
        history_text = "\n".join([f"{m['role']}: {m['text'] if 'text' in m else m.get('data', {}).get('answer', '')}" for m in (history or [])[-5:]])
        
        topic_prompt = (
            "You are a Research Director. Based on the conversation, identify the SINGLE most important Wikipedia TOPIC we are discussing.\n"
            "If the question is about a specific detail (like 'launch date'), identify the PARENT entity (like 'Apollo 11').\n"
            f"History:\n{history_text}\n"
            f"Current Question: {question}\n\n"
            "Return ONLY the plain name of the Wikipedia article. No other text."
        )
        target_topic = self.llm.simple_generate(topic_prompt).strip().strip('"').strip("'")
        # Self-correction: if the AI gives a full sentence, take the last capitalized part or just the main subject
        if "topic is" in target_topic.lower(): target_topic = target_topic.split("is")[-1].strip()

        try:
            # 2. SOURCE EXTRACTION: Fetch and Index the master article
            logger.info(f"Targeting Topic: {target_topic}")
            article = self.wiki.get_article(target_topic)
            title = article["title"]
            
            # Ensure the source article is 100% in our vector brain
            if not self.chroma.exists(title):
                self.chroma.add_article(title, article["content"])
                self.cache.add(title, article["url"], 0)

            # 3. DEEP RETRIEVAL: Pull specific facts from that locked article
            query_embedding = self.embedder.embed_query(question)
            # Use extra deep vision (top_k=25) for the locked topic
            results = self.chroma.search(query_embedding, top_k=25)
            
            # Extract and Order: Summary first, then relevant snippets
            id_to_chunk = {id: d for d, id in zip(results.get("documents", [[]])[0], results.get("ids", [[]])[0])}
            sorted_all_ids = sorted(id_to_chunk.keys(), key=lambda x: int(x.split('_')[-1]) if '_' in x else 0)
            
            # Mandatory Lead Section (first 4 chunks)
            intro_chunks = [id_to_chunk[id] for id in sorted_all_ids if int(id.split('_')[-1]) < 4]
            best_retrieved = results["documents"][0]
            
            # Combine without duplicates, keeping order
            context = "\n\n".join(intro_chunks + [c for c in best_retrieved if c not in intro_chunks])
            
            # 4. FINAL ANSWER: Generate using ONLY the locked article's context
            answer = self.llm.generate(question=question, context=context)

            return {
                "answer": answer,
                "article": title,
                "wikipedia_url": article["url"],
                "sources": [],
                "images": article["images"],
                "matched_query": target_topic,
                "cache_hit": True,
                "response_time": round(time.time() - start, 2),
                "model": "Groq Llama-3",
                "spelling_corrected": article.get("spelling_corrected", False)
            }
        except Exception as e:
            logger.error(f"Topic Error: {e}")
            logger.error(traceback.format_exc())
            return {
                "answer": "I hit a snag while researching that topic. Could you be more specific about the subject?",
                "article": "Research Error",
                "wikipedia_url": "",
                "sources": [],
                "images": [],
                "matched_query": target_topic,
                "cache_hit": False,
                "response_time": 0,
                "model": "error",
                "spelling_corrected": False
            }