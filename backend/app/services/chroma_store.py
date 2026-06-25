import chromadb
import logging
from backend.app.config.settings import (
    CHROMA_DB_PATH,
    CHROMA_COLLECTION_NAME,
)

logger = logging.getLogger(__name__)

class ChromaStore:
    def __init__(self):
        # Create persistent client
        self.client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME
        )

    def add_article(self, title: str, content: str):
        """
        Chunk content and add to ChromaDB.
        """
        # Split by paragraph
        paragraphs = [p.strip() for p in content.split("\n\n") if len(p.strip()) > 50]
        
        if not paragraphs:
            return

        ids = [f"{title}_{i}" for i in range(len(paragraphs))]
        metadatas = [{"title": title} for _ in range(len(paragraphs))]
        
        self.collection.add(
            documents=paragraphs,
            ids=ids,
            metadatas=metadatas
        )
        logger.info(f"Added {len(paragraphs)} paragraphs from '{title}' to ChromaDB.")

    def search(self, query_embedding, top_k: int = 5):
        """
        Search for most similar paragraphs. 
        Note: We use the embedding provided by EmbeddingService.
        """
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )

    def clear(self):
        """
        Reset collection.
        """
        self.client.delete_collection(CHROMA_COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME
        )
