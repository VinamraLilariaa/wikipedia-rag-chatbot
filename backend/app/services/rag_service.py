import time
import logging
import traceback
import re
from concurrent.futures import ThreadPoolExecutor

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
        self.executor = ThreadPoolExecutor(max_workers=2)

    def ask(self, question: str, history: list = None):
        start = time.time()
        
        # 1. OPTIMIZED TOPIC DISCOVERY
        # If it's the first question, just use it directly to save a Groq call
        if not history or len(history) == 0:
            target_topics = [question]
            subjects_raw = question
        else:
            history_text = "\n".join([f"{m['role']}: {m['text'] if 'text' in m else m.get('data', {}).get('answer', '')}" for m in (history or [])[-3:]])
            topic_prompt = (
                "Identify the ONE or TWO main Wikipedia subjects for the current question.\n"
                "Return only names separated by a comma.\n"
                f"History:\n{history_text}\n"
                f"Question: {question}\n\n"
                "Names:"
            )
            subjects_raw = self.llm.simple_generate(topic_prompt).strip().strip('"').strip("'")
            if "Names:" in subjects_raw: subjects_raw = subjects_raw.split("Names:")[-1].strip()
            target_topics = list(dict.fromkeys([s.strip() for s in subjects_raw.split(",") if len(s.strip()) > 2]))[:2]

        if not target_topics: target_topics = [question]

        try:
            # 2. SOURCE EXTRACTION (Sequential but cached)
            all_intro_chunks = []
            all_retrieved_chunks = []
            final_title = ""
            final_url = ""
            final_images = []

            for topic in target_topics:
                try:
                    # Wikipedia search is the bottleneck, cached results are instant
                    article = self.wiki.get_article(topic)
                    title = article["title"]
                    
                    if not final_title:
                        final_title = title
                        final_url = article["url"]
                        final_images = article["images"]
                    
                    # Indexing is fast with the new regex chunker
                    if not self.chroma.exists(title):
                        self.chroma.add_article(title, article["content"])
                        self.cache.add(title, article["url"], 0)

                    # Quick retrieval
                    query_embedding = self.embedder.embed_query(f"{question} {topic}")
                    results = self.chroma.search(query_embedding, top_k=15)
                    
                    id_to_chunk = {id: d for d, id in zip(results.get("documents", [[]])[0], results.get("ids", [[]])[0])}
                    sorted_ids = sorted(id_to_chunk.keys(), key=lambda x: int(x.split('_')[-1]) if '_' in x else 0)
                    
                    all_intro_chunks.extend([id_to_chunk[id] for id in sorted_ids if int(id.split('_')[-1]) < 4])
                    all_retrieved_chunks.extend(results["documents"][0])
                except Exception:
                    continue

            # 3. NITRO CONTEXT: Flatten and deduplicate
            context = "\n\n".join(list(dict.fromkeys(all_intro_chunks + all_retrieved_chunks)))
            
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
            logger.error(f"Nitro Error: {e}")
            return {
                "answer": "I'm still processing that. Please try a different way of asking.",
                "article": "Performance Delay",
                "wikipedia_url": "",
                "sources": [],
                "images": [],
                "matched_query": subjects_raw,
                "cache_hit": False,
                "response_time": 0,
                "model": "error",
                "spelling_corrected": False
            }