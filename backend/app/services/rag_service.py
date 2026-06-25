import time

from backend.app.config.settings import TOP_K
from backend.app.services.cache_service import CacheService
from backend.app.services.embedding_service import EmbeddingService
from backend.app.services.llm_service import LLMService
from backend.app.services.wikipedia_service import WikipediaService
from backend.app.utils.cleaner import TextCleaner
from backend.app.utils.chunker import TextChunker
from backend.app.utils.logger import logger
from backend.app.vectorstore.chroma_store import ChromaStore


class RAGService:
    """
    Coordinates the complete Retrieval-Augmented Generation (RAG) pipeline.
    """

    def __init__(self):

        logger.info("Initializing RAG Service...")

        self.wikipedia = WikipediaService()

        self.cleaner = TextCleaner()

        self.chunker = TextChunker()

        self.embedder = EmbeddingService()

        self.chroma = ChromaStore()

        self.cache = CacheService()

        self.llm = LLMService()

        logger.info("RAG Service initialized successfully.")

    def _index_article(self, question: str):

        article = self.wikipedia.get_article(question)

        title = article["title"]

        logger.info(f"Retrieved article: {title}")

        cache_hit = self.cache.exists(title)

        if cache_hit:

            logger.info(f"Cache hit for '{title}'.")

        else:

            logger.info(f"Cache miss for '{title}'.")

        already_indexed = self.chroma.article_exists(title)

        if already_indexed:

            logger.info(
                f"Article '{title}' already exists in ChromaDB."
            )

            return article, True

        logger.info("Cleaning article...")

        cleaned = self.cleaner.clean(
            article["content"]
        )

        logger.info("Chunking article...")

        chunks = self.chunker.split(
            cleaned
        )

        logger.info(
            f"Generated {len(chunks)} chunks."
        )

        logger.info("Generating embeddings...")

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

        logger.info("Saving vectors to ChromaDB...")

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

        logger.info("Article indexed successfully.")

        return article, False

    def ask(self, question: str):

        logger.info("=" * 60)

        logger.info(f"User Question: {question}")

        start = time.time()

        article, cache_hit = self._index_article(question)

        logger.info("Embedding user query...")

        query_embedding = self.embedder.embed_query(
            question
        )

        logger.info("Searching ChromaDB...")

        results = self.chroma.search(

            query_embedding,

            top_k=TOP_K,
        )

        if (

            "documents" not in results

            or not results["documents"]

            or not results["documents"][0]

        ):

            raise Exception(
                "No relevant documents found."
            )

        retrieved_chunks = results["documents"][0]

        logger.info(
            f"Retrieved {len(retrieved_chunks)} chunks."
        )

        context = "\n\n".join(
            retrieved_chunks
        )

        logger.info("Generating answer using Groq...")

        answer = self.llm.generate(

            question=question,

            context=context,
        )

        response_time = round(

            time.time() - start,

            2,
        )

        logger.info(
            f"Completed in {response_time} seconds."
        )

        logger.info("=" * 60)

        return {

            "answer": answer,

            "article": article["title"],

            "wikipedia_url": article["url"],

            "sources": retrieved_chunks,

            "cache_hit": cache_hit,

            "response_time": response_time,

            "model": "llama-3.3-70b-versatile",
        }