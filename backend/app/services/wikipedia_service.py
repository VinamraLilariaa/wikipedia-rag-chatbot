import wikipedia
import logging
from backend.app.utils.logger import logger

# Configure the library for speed and compliance
wikipedia.set_rate_limiting(False)
wikipedia.set_lang("en")

class WikipediaService:
    def __init__(self):
        # We identify as a research project to ensure Wikipedia's servers prioritize us
        wikipedia.set_user_agent("WikiIntelBot/1.0 (Contact: researcher@example.com; Research Project)")

    def get_article(self, query: str) -> dict:
        """
        OFFICIAL LIBRARY ACCESS: The most stable and robust method for 
        retrieving Wikipedia data on cloud servers.
        """
        try:
            # 1. Search and Auto-Suggest (Handles misspellings and redirects)
            search_title = wikipedia.suggest(query) or query
            
            # 2. Page Acquisition (Handles disambiguation and missing pages)
            try:
                page = wikipedia.page(search_title, auto_suggest=True)
            except wikipedia.DisambiguationError as e:
                # If there are multiple options, pick the first one
                page = wikipedia.page(e.options[0])
            except wikipedia.PageError:
                # Try the raw query if suggestion failed
                page = wikipedia.page(query)

            # 3. Data Formatting
            return {
                "title": page.title,
                "url": page.url,
                "content": page.summary + "\n\n" + page.content[:50000],
                "images": [{"url": img, "caption": page.title} for img in page.images[:6] if "upload" in img and not any(x in img.lower() for x in ('svg', 'icon', 'stub', 'edit', 'magnify'))]
            }
        except Exception as e:
            logger.error(f"Wikipedia Library Failure: {e}")
            raise ValueError(f"Could not retrieve Wikipedia content for '{query}'.")