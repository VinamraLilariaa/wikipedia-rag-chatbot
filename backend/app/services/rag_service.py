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
        
        # 1. ADVANCED TOPIC DISCOVERY: Identify Primary and Secondary subjects
        history_text = "\n".join([f"{m['role']}: {m['text'] if 'text' in m else m.get('data', {}).get('answer', '')}" for m in (history or [])[-5:]])
        
        topic_prompt = (
            "You are a Research Director. Identify the SUBJECTS of this conversation.\n"
            "Return the names of the TWO most relevant Wikipedia articles, separated by a comma (e.g., 'Virat Kohli, Cricket').\n"
            "If only one subject exists, return just one name.\n"
            "If 'he' or 'she' is used, include the full name of the person they refer to.\n"
            f"History:\n{history_text}\n"
            f"Current Question: {question}\n\n"
            "Names:"
        )
        subjects_raw = self.llm.simple_generate(topic_prompt).strip().strip('"').strip("'")
        if "Names:" in subjects_raw: subjects_raw = subjects_raw.split("Names:")[-1].strip()
        
        target_topics = [s.strip() for s in subjects_raw.split(",") if len(s.strip()) > 2][:2]
        if not target_topics: target_topics = [question]

        try:
            # 2. MULTI-SOURCE EXTRACTION
            all_intro_chunks = []
            all_retrieved_chunks = []
            final_title = ""
            final_url = ""
            final_images = []

            for topic in target_topics:
                try:
                    article = self.wiki.get_article(topic)
                    title = article["title"]
                    if not final_title: 
                        final_title = title
                        final_url = article["url"]
                        final_images = article["images"]
                    
                    if not self.chroma.exists(title):
                        self.chroma.add_article(title, article["content"])
                        self.cache.add(title, article["url"], 0)

                    # Retrieval for this specific topic
                    query_embedding = self.embedder.embed_query(f"{question} ({topic})")
                    results = self.chroma.search(query_embedding, top_k=15)
                    
                    # Extract chunks
                    id_to_chunk = {id: d for d, id in zip(results.get("documents", [[]])[0], results.get("ids", [[]])[0])}
                    sorted_all_ids = sorted(id_to_chunk.keys(), key=lambda x: int(x.split('_')[-1]) if '_' in x else 0)
                    
                    # Intro chunks (first 4)
                    topic_intros = [id_to_chunk[id] for id in sorted_all_ids if int(id.split('_')[-1]) < 4]
                    topic_retrieved = results["documents"][0]
                    
                    all_intro_chunks.extend(topic_intros)
                    all_retrieved_chunks.extend(topic_retrieved)
                except Exception as e:
                    logger.warning(f"Failed to fetch topic '{topic}': {e}")

            # 3. CONTEXT INTEGRATION: Combine knowledge from all sources
            context_list = list(dict.fromkeys(all_intro_chunks + all_retrieved_chunks))
            context = "\n\n".join(context_list)
            
            # 4. FINAL GROUNDED ANSWER
            answer = self.llm.generate(question=question, context=context)

            return {
                "answer": answer,
                "article": final_title,
                "wikipedia_url": final_url,
                "sources": target_topics,
                "images": final_images,
                "matched_query": subjects_raw,
                "cache_hit": True,
                "response_time": round(time.time() - start, 2),
                "model": "Groq Llama-3",
                "spelling_corrected": False
            }
        except Exception as e:
            logger.error(f"Multi-Topic Error: {e}")
            return {
                "answer": "I hit a snag while researching. Please try a different question.",
                "article": "Error",
                "wikipedia_url": "",
                "sources": [],
                "images": [],
                "matched_query": subjects_raw,
                "cache_hit": False,
                "response_time": 0,
                "model": "error",
                "spelling_corrected": False
            }