import time

import wikipedia
import wikipediaapi
from requests.exceptions import HTTPError

from backend.app.utils.logger import logger


class WikipediaService:

    def __init__(self):

        wikipedia.set_lang("en")

        self.wiki = wikipediaapi.Wikipedia(
            language="en",
            user_agent="WikipediaRAGBot/1.0 (tanav-project)",
        )

    def search_article(self, query: str) -> str:

        logger.info(f"Searching Wikipedia for: {query}")

        retries = 3

        for attempt in range(retries):

            try:

                results = wikipedia.search(query, results=5)

                if not results:
                    raise ValueError(
                        f"No Wikipedia article found for '{query}'."
                    )

                logger.info(f"Selected article: {results[0]}")

                return results[0]

            except HTTPError as e:

                if "429" in str(e):

                    wait = 2 ** attempt

                    logger.warning(
                        f"Wikipedia rate limited. Retrying in {wait} seconds..."
                    )

                    time.sleep(wait)

                else:
                    raise

            except Exception:

                if attempt == retries - 1:
                    raise

                time.sleep(2)

        raise Exception("Wikipedia search failed after multiple retries.")

    def get_article(self, query: str):

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