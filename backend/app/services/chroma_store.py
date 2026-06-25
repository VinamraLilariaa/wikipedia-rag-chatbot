import logging
import uuid

logger = logging.getLogger(__name__)

class ChromaStore:
    def __init__(self):
        """
        SMART-MEMORY STORE: Replaces ChromaDB with a lightweight RAM buffer.
        No database locks, no crashes, no memory errors.
        """
        self.registry = {} # Stores article titles
        self.memory = {}   # Stores actual chunks

    def exists(self, title: str) -> bool:
        return title in self.registry

    def add_article(self, title: str, content: str):
        """Cleanly chunks text into RAM for fuzzy searching."""
        self.registry[title] = True
        
        # Split into logical 800-character chunks for the LLM
        chunks = []
        clean_text = content.replace('\n\n', '\n').strip()
        raw_chunks = [clean_text[i:i+800] for i in range(0, len(clean_text), 600)]
        
        self.memory[title] = raw_chunks
        logger.info(f"Indexed {len(raw_chunks)} Shadow-Chunks for {title}")

    def get_all_chunks(self, title: str):
        return self.memory.get(title, [])

    def search(self, *args, **kwargs):
        """The search is now handled by the Shadow Engine (EmbeddingService)."""
        pass
