import requests
import wikipediaapi

from backend.app.utils.logger import logger

class WikipediaService:
    """
    Service for searching and retrieving Wikipedia articles.
    """

    SEARCH_URL = "https://en.wikipedia.org/w/api.php"

    def __init__(self):
        self.wiki = wikipediaapi.Wikipedia(
            language="en",
            user_agent="WikipediaRAG/1.0"
        )

    def search_article(self, query: str) -> str:
        """
        Search Wikipedia and return the best matching article title.
        """

        logger.info(f"Searching Wikipedia for: {query}")

        response = requests.get(
            self.SEARCH_URL,
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
            },
            timeout=10,
        )

        response.raise_for_status()

        results = response.json()["query"]["search"]

        if not results:
            raise ValueError(
                f"No Wikipedia article found for '{query}'."
            )

        title = results[0]["title"]

        logger.info(f"Best match: {title}")

        return title

    def get_article(self, query: str) -> dict:
        """
        Download the best matching Wikipedia article.
        """

        title = self.search_article(query)

        page = self.wiki.page(title)

        if not page.exists():
            raise ValueError(
                f"Wikipedia page '{title}' does not exist."
            )

        logger.info(f"Downloaded article: {page.title}")

        return {
            "title": page.title,
            "url": page.fullurl,
            "content": page.text,
        }