import requests
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
        Two-step Wikipedia Action API fetch:
        1. Search for the best matching title
        2. Fetch full plaintext extract + thumbnail
        """
        # Step 1: Search
        search_data = self.session.get(WIKI_API, params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 1,
        }, timeout=10).json()

        results = search_data.get("query", {}).get("search", [])
        if not results:
            raise ValueError(f"No Wikipedia article found for: '{query}'")

        title = results[0]["title"]

        # Step 2: Fetch full article text (plain text, not HTML)
        fetch_data = self.session.get(WIKI_API, params={
            "action": "query",
            "prop": "extracts|pageimages|info",
            "explaintext": True,
            "exsectionformat": "plain",
            "exlimit": 1,
            "titles": title,
            "format": "json",
            "inprop": "url",
            "pithumbsize": 500,
            "redirects": 1,
        }, timeout=15).json()

        pages = fetch_data.get("query", {}).get("pages", {})

        for pid, page in pages.items():
            if pid == "-1" or "extract" not in page:
                raise ValueError(f"Wikipedia returned no content for: '{title}'")

            images = []
            if "thumbnail" in page:
                images = [{"url": page["thumbnail"]["source"], "caption": page["title"]}]

            return {
                "title": page["title"],
                "url": page.get("fullurl", f"{WIKI_BASE}/wiki/{quote(title.replace(' ', '_'))}"),
                "content": page["extract"],  # Full article — NOT a summary
                "images": images,
            }

        raise ValueError(f"Empty response from Wikipedia for: '{title}'")