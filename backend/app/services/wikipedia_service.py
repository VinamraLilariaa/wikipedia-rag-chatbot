import time

import wikipedia
from requests.exceptions import HTTPError

from backend.app.utils.logger import logger


class WikipediaService:

    def __init__(self):

        wikipedia.set_lang("en")

    def get_article(self, query: str):

        retries = 3

        for attempt in range(retries):

            try:

                logger.info(f"Searching Wikipedia for: {query}")

                results = wikipedia.search(
                    query,
                    results=5,
                )

                if not results:
                    raise ValueError(
                        f"No Wikipedia article found for '{query}'."
                    )

                title = results[0]

                logger.info(
                    f"Selected article: {title}"
                )

                page = wikipedia.page(
                    title,
                    auto_suggest=False,
                )

                logger.info(
                    f"Downloaded article: {page.title}"
                )

                return {
                    "title": page.title,
                    "url": page.url,
                    "content": page.content,
                }

            except wikipedia.DisambiguationError as e:

                logger.warning(
                    "Disambiguation page encountered."
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

        raise Exception(
            "Wikipedia search failed after multiple retries."
        )