import requests
import re
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)

WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKI_BASE = "https://en.wikipedia.org"

class WikipediaService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "WikiIntelBot/1.0 (https://huggingface.co; educational research)",
            "Accept-Encoding": "gzip",
        })

    def get_article(self, query: str) -> dict:
        """
        Fetch full Wikipedia article via the Action API.
        Step 1: Search for the best matching title.
        Step 2: Fetch full extract + thumbnail.
        """
        # Step 1: Search
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 1,
        }
        search_resp = self.session.get(WIKI_API, params=search_params, timeout=10)
        search_resp.raise_for_status()
        results = search_resp.json().get("query", {}).get("search", [])

        if not results:
            raise ValueError(f"No Wikipedia article found for '{query}'")

        title = results[0]["title"]

        # Step 2: Fetch full extract + image
        fetch_params = {
            "action": "query",
            "prop": "extracts|pageimages|info",
            "explaintext": True,       # plain text, no HTML
            "exsectionformat": "plain",
            "titles": title,
            "format": "json",
            "inprop": "url",
            "pithumbsize": 500,
            "redirects": 1,
        }
        fetch_resp = self.session.get(WIKI_API, params=fetch_params, timeout=15)
        fetch_resp.raise_for_status()
        pages = fetch_resp.json().get("query", {}).get("pages", {})

        for pid, page in pages.items():
            if "extract" not in page:
                raise ValueError(f"Wikipedia returned no content for '{title}'")

            content = page["extract"]  # Full plain-text article
            images = []
            if "thumbnail" in page:
                images = [{"url": page["thumbnail"]["source"], "caption": title}]

            return {
                "title": page["title"],
                "url": page.get("fullurl", f"{WIKI_BASE}/wiki/{quote(title.replace(' ', '_'))}"),
                "content": content,   # Full article text — NOT just a summary
                "images": images,
            }

        raise ValueError(f"Could not parse Wikipedia response for '{title}'")