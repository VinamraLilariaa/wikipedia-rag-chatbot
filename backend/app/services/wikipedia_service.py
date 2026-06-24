import requests
import wikipediaapi
from rapidfuzz import fuzz

from backend.app.utils.logger import logger


class WikipediaService:
    SEARCH_URL = "https://en.wikipedia.org/w/api.php"

    def __init__(self):
        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": "WikipediaRAGBot/1.0 (tanav-project)"
        })

        self.wiki = wikipediaapi.Wikipedia(
            language="en",
            user_agent="WikipediaRAGBot/1.0 (tanav-project)"
        )

    def search_article(self, query: str) -> str:

        logger.info(f"Searching for: {query}")

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
            raise ValueError(
                f"No Wikipedia article found for '{query}'."
            )

        # -------------------------------
        # Fuzzy ranking of Wikipedia titles
        # -------------------------------

        best_title = None
        best_score = -1

        for article in results:

            title = article["title"]

            score = fuzz.token_sort_ratio(
                query.lower(),
                title.lower()
            )

            logger.info(
                f"{title} --> {score}"
            )

            if score > best_score:
                best_score = score
                best_title = title

        logger.info(
            f"Chosen Article: {best_title} ({best_score})"
        )

        return best_title

    def get_article(self, query: str):

        title = self.search_article(query)

        page = self.wiki.page(title)

        if not page.exists():
            raise ValueError(
                f"Wikipedia page '{title}' does not exist."
            )

        logger.info(
            f"Downloaded article: {page.title}"
        )

        return {
            "title": page.title,
            "url": page.fullurl,
            "content": page.text,
        }