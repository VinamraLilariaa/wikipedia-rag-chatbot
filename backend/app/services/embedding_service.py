from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """
    Handles generation of sentence embeddings.
    """

    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def embed_documents(self, documents: list):
        """
        Generate embeddings for multiple chunks.
        """
        return self.model.encode(
            documents,
            convert_to_numpy=True,
            show_progress_bar=True,
        )

    def embed_query(self, query: str):
        """
        Generate embedding for a user question.
        """
        return self.model.encode(
            query,
            convert_to_numpy=True,
        )