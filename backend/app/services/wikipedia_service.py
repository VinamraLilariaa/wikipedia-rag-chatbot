import wikipedia
from rapidfuzz import fuzz

from backend.app.utils.logger import logger


class WikipediaService:

    def __init__(self):

        wikipedia.set_lang("en")

        self.title_cache = {}

    def search_article(self, query: str):

        query = query.strip()

        if query.lower() in self.title_cache:
            return self.title_cache[query.lower()]

        try:
            suggestion = wikipedia.suggest(query)

            if suggestion:
                self.title_cache[query.lower()] = suggestion
                return suggestion

        except Exception:
            pass

        results = wikipedia.search(query, results=10)

        if not results:
            raise ValueError(f"No article found for '{query}'.")

        best_title = results[0]
        best_score = -1

        for title in results:

            score = max(
                fuzz.ratio(query.lower(), title.lower()),
                fuzz.partial_ratio(query.lower(), title.lower()),
                fuzz.token_sort_ratio(query.lower(), title.lower()),
                fuzz.token_set_ratio(query.lower(), title.lower()),
            )

            if score > best_score:
                best_score = score
                best_title = title

        self.title_cache[query.lower()] = best_title

        return best_title

    def get_article(self, query: str):

        title = self.search_article(query)

        page = wikipedia.page(
            title,
            auto_suggest=False,
        )

        return {
            "title": page.title,
            "url": page.url,
            "content": page.content,
        }