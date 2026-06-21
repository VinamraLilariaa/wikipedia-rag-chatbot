import time

from backend.app.config.settings import TOP_K
from backend.app.services.cache_service import CacheService
from backend.app.services.embedding_service import EmbeddingService
from backend.app.services.llm_service import LLMService
from backend.app.services.wikipedia_service import WikipediaService
from backend.app.utils.cleaner import TextCleaner
from backend.app.utils.chunker import TextChunker
from backend.app.vectorstore.chroma_store import ChromaStore


class RAGService:

    def __init__(self):

        self.wikipedia = WikipediaService()
        self.cleaner = TextCleaner()
        self.chunker = TextChunker()

        self.embedder = EmbeddingService()
        self.chroma = ChromaStore()

        self.cache = CacheService()

        self.llm = LLMService()

    def _index_article(self, question: str):

        article = self.wikipedia.get_article(question)

        title = article["title"]

        cache_hit = self.cache.exists(title)

        # Prevent duplicate indexing
        if (not cache_hit) and (not self.chroma.article_exists(title)):

            cleaned = self.cleaner.clean(
                article["content"]
            )

            chunks = self.chunker.split(
                cleaned
            )

            embeddings = self.embedder.embed_documents(
                chunks
            )

            ids = [
                f"{title}_{i}"
                for i in range(len(chunks))
            ]

            metadatas = [
                {
                    "article": title,
                    "url": article["url"],
                    "chunk": i,
                }
                for i in range(len(chunks))
            ]

            self.chroma.add_documents(
                ids=ids,
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas,
            )

            self.cache.add(
                title=title,
                url=article["url"],
                chunk_count=len(chunks),
            )

        return article, cache_hit

    def ask(self, question: str):

        start = time.time()

        article, cache_hit = self._index_article(question)

        query_embedding = self.embedder.embed_query(question)

        results = self.chroma.search(
            query_embedding,
            top_k=TOP_K,
        )

        if (
            "documents" not in results
            or not results["documents"]
            or not results["documents"][0]
        ):
            raise Exception("No relevant documents found.")

        retrieved_chunks = results["documents"][0]

        context = "\n\n".join(retrieved_chunks)

        answer = self.llm.generate(
            question=question,
            context=context,
        )

        response_time = round(
            time.time() - start,
            2,
        )

        return {
            "answer": answer,
            "article": article["title"],
            "wikipedia_url": article["url"],
            "sources": retrieved_chunks,
            "cache_hit": cache_hit,
            "response_time": response_time,
            "model": "qwen3:4b",
        }