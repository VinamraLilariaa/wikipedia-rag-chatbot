import time

import wikipedia

from backend.app.services.search_service import SearchService
from backend.app.utils.logger import logger


class WikipediaService:
    """
    Responsible only for downloading Wikipedia articles.
    Article selection is delegated to SearchService.
    """

    def __init__(self):

        wikipedia.set_lang("en")

        self.search_service = SearchService()

    def get_article(self, query: str):

        retries = 3

        for attempt in range(retries):

            try:

                title = self.search_service.search(query)

                logger.info(
                    f"Downloading article: {title}"
                )

                page = wikipedia.page(
                    title,
                    auto_suggest=False,
                )

                logger.info(
                    f"Downloaded: {page.title}"
                )

                return {

                    "title": page.title,

                    "url": page.url,

                    "content": page.content,
                }

            except wikipedia.DisambiguationError as e:

                logger.warning(
                    f"Disambiguation encountered for '{query}'. "
                    f"Trying '{e.options[0]}'."
                )

                page = wikipedia.page(
                    e.options[0],
                    auto_suggest=False,
                )

                return {

                    "title": page.title,

                    "url": page.url,

                    "content": page.content,
                }

            except wikipedia.PageError:

                raise ValueError(
                    f"No Wikipedia page found for '{query}'."
                )

            except Exception as e:

                logger.warning(
                    f"Attempt {attempt + 1} failed: {e}"
                )

                if attempt == retries - 1:
                    raise

                time.sleep(2 ** attempt)

        raise Exception(
            "Unable to retrieve article after multiple retries."
        )