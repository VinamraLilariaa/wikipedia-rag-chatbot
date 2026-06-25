import chromadb
from chromadb.config import Settings

from backend.app.config.settings import CHROMA_PATH


class ChromaStore:
    """
    Handles storing and retrieving embeddings from ChromaDB.
    """

    def __init__(self):

        self.client = chromadb.Client(
            Settings(
            anonymized_telemetry=False
        )
    )

        self.collection = self.client.get_or_create_collection(
            name="wikipedia_articles"
        )

    def add_documents(
        self,
        ids: list,
        documents: list,
        embeddings,
        metadatas: list,
    ):
        """
        Store document chunks.
        """

        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings.tolist(),
            metadatas=metadatas,
        )

    def search(
        self,
        embedding,
        top_k: int = 5,
    ):
        """
        Retrieve the most similar chunks.
        """

        return self.collection.query(
            query_embeddings=[embedding.tolist()],
            n_results=top_k,
        )

    def article_exists(
        self,
        title: str,
    ) -> bool:
        """
        Check whether an article has already been indexed.
        """

        result = self.collection.get(
            where={"article": title}
        )

        return len(result["ids"]) > 0

    def get_article_chunks(
        self,
        title: str,
    ):
        """
        Return all chunks belonging to an article.
        """

        return self.collection.get(
            where={"article": title}
        )

    def count(self) -> int:
        """
        Number of stored chunks.
        """

        return self.collection.count()

    def clear(self):
        """
        Delete all stored vectors.
        """

        ids = self.collection.get()["ids"]

        if ids:
            self.collection.delete(ids=ids)