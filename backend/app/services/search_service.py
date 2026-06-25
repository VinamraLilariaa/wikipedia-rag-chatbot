import re

import wikipedia
from rapidfuzz import fuzz

from backend.app.utils.logger import logger


class SearchService:
    """
    Intelligent search service responsible for:

    - Cleaning user queries
    - Searching Wikipedia
    - Ranking results using RapidFuzz
    - Returning the best matching article
    """

    def __init__(self):

        wikipedia.set_lang("en")

    def normalize(self, text: str) -> str:
        """
        Normalize user query for better matching.
        """

        text = text.lower()

        text = re.sub(
            r"[^a-z0-9 ]",
            "",
            text,
        )

        text = " ".join(text.split())

        return text

    def score(
        self,
        query: str,
        title: str,
    ) -> float:
        """
        Compute similarity score using multiple
        RapidFuzz algorithms.
        """

        query = self.normalize(query)

        title = self.normalize(title)

        scores = [

            fuzz.ratio(
                query,
                title,
            ),

            fuzz.partial_ratio(
                query,
                title,
            ),

            fuzz.token_sort_ratio(
                query,
                title,
            ),

            fuzz.token_set_ratio(
                query,
                title,
            ),
        ]

        return max(scores)

    def search(
        self,
        query: str,
    ) -> str:
        """
        Search Wikipedia and return the best title.
        """

        logger.info(
            f"Searching Wikipedia for '{query}'"
        )

        results = wikipedia.search(
            query,
            results=10,
        )

        if not results:

            raise ValueError(
                f"No article found for '{query}'."
            )

        logger.info(
            "Wikipedia Results:"
        )

        for result in results:

            logger.info(result)

        best_title = None

        best_score = -1

        for title in results:

            score = self.score(
                query,
                title,
            )

            logger.info(
                f"{title} --> {score}"
            )

            if score > best_score:

                best_score = score

                best_title = title

        logger.info(
            f"Selected: {best_title}"
        )

        return best_title