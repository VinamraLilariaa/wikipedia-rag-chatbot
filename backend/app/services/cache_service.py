import json
from datetime import datetime

from backend.app.config.settings import (
    EMBEDDING_MODEL,
    CACHE_FILE,
)

class CacheService:
    """
    Handles cache metadata for processed Wikipedia articles.
    """

    def __init__(self):

        self.cache_file = CACHE_FILE

        if not self.cache_file.exists():
            self.cache_file.write_text("{}")

    def _load_cache(self) -> dict:
        """
        Load cache metadata from JSON file.
        """

        with open(self.cache_file, "r") as f:
            return json.load(f)

    def _save_cache(self, data: dict):
        """
        Save cache metadata.
        """

        with open(self.cache_file, "w") as f:
            json.dump(
                data,
                f,
                indent=4
            )

    def exists(
        self,
        title: str,
    ) -> bool:
        """
        Check whether an article is already cached.
        """

        cache = self._load_cache()

        return title in cache

    def add(
        self,
        title: str,
        url: str,
        chunk_count: int,
    ):
        """
        Store article metadata.
        """

        cache = self._load_cache()

        cache[title] = {

            "title": title,

            "url": url,

            "cached_at": datetime.now().isoformat(),

            "embedding_model": EMBEDDING_MODEL,

            "chunk_count": chunk_count,
        }

        self._save_cache(cache)

    def get(
        self,
        title: str,
    ):

        cache = self._load_cache()

        return cache.get(title)

    def clear(self):
        """
        Remove all cache metadata.
        """

        self._save_cache({})

    def stats(self):
        """
        Return cache statistics.
        """

        cache = self._load_cache()

        return {

            "cached_articles": len(cache),

            "articles": list(cache.keys())
        }