import wikipedia
import wikipediaapi
from rapidfuzz import fuzz

from backend.app.utils.logger import logger


class WikipediaService:

    def __init__(self):

        wikipedia.set_lang("en")

        self.wiki = wikipediaapi.Wikipedia(
            language="en",
            user_agent="WikipediaRAGBot/1.0"
        )

        # cache for resolved titles
        self.title_cache = {}

    def search_article(self, query: str):

        query = query.strip()

        if query.lower() in self.title_cache:
            logger.info(f"Cache hit: {query}")
            return self.title_cache[query]

        logger.info(f"Searching Wikipedia for: {query}")

        # -------------------------
        # Step 1 : Wikipedia Suggest
        # -------------------------

        try:
            suggestion = wikipedia.suggest(query)

            if suggestion:
                logger.info(f"Suggestion -> {suggestion}")

                self.title_cache[query.lower()] = suggestion
                return suggestion

        except Exception:
            pass

        # -------------------------
        # Step 2 : Wikipedia Search
        # -------------------------

        try:
            results = wikipedia.search(query, results=10)

        except Exception:
            results = []

        if not results:
            raise ValueError(f"No article found for '{query}'.")

        # -------------------------
        # Step 3 : RapidFuzz Ranking
        # -------------------------

        best_title = results[0]
        best_score = -1

        for title in results:

            score = fuzz.token_sort_ratio(
                query.lower(),
                title.lower()
            )

            logger.info(f"{title} -> {score}")

            if score > best_score:
                best_score = score
                best_title = title

        logger.info(f"Chosen article: {best_title}")

        self.title_cache[query.lower()] = best_title

        return best_title

    def get_article(self, query: str):

        title = self.search_article(query)

        page = self.wiki.page(title)

        if not page.exists():
            raise ValueError(f"No Wikipedia page found for '{title}'.")

        return {
            "title": page.title,
            "url": page.fullurl,
            "content": page.text,
        }