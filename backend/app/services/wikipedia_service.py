import requests
from rapidfuzz import fuzz

from backend.app.utils.logger import logger


class WikipediaService:

    SEARCH_URL = "https://en.wikipedia.org/w/api.php"

    def __init__(self):

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": "WikipediaRAGBot/1.0 (tanav-project)"
        })

        self.title_cache = {}

    def search_article(self, query: str):

        query = query.strip()

        if query.lower() in self.title_cache:
            return self.title_cache[query.lower()]

        logger.info(f"Searching Wikipedia for: {query}")

        response = self.session.get(
            self.SEARCH_URL,
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": 10,
                "format": "json",
            },
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        results = data.get("query", {}).get("search", [])

        if not results:
            raise ValueError(f"No article found for '{query}'.")

        best_title = None
        best_score = -1

        for article in results:

            title = article["title"]

            score = max(
                fuzz.ratio(query.lower(), title.lower()),
                fuzz.partial_ratio(query.lower(), title.lower()),
                fuzz.token_sort_ratio(query.lower(), title.lower()),
                fuzz.token_set_ratio(query.lower(), title.lower()),
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

        response = self.session.get(
            self.SEARCH_URL,
            params={
                "action": "query",
                "prop": "extracts|info",
                "titles": title,
                "inprop": "url",
                "explaintext": True,
                "exlimit": 1,
                "format": "json",
            },
            timeout=10,
        )

        response.raise_for_status()

        pages = response.json()["query"]["pages"]

        page = next(iter(pages.values()))

        if "missing" in page:
            raise ValueError(f"No Wikipedia page found for '{title}'.")

        return {
            "title": page["title"],
            "url": page["fullurl"],
            "content": page["extract"],
        }