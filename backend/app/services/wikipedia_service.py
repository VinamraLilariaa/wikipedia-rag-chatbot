import requests
import re
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)

class WikipediaService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "WikiIntel/1.0 (Research Project; Contact: dev@example.com)"
        })

    def get_article(self, query: str) -> dict:
        """
        Ultra-Stable REST Retrieval.
        """
        try:
            # 1. Direct Summary Hit
            search_title = query.strip().replace(' ', '_')
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(search_title)}"
            resp = self.session.get(url, timeout=10)
            
            if resp.status_code != 200:
                # Fallback to search
                search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote(query)}&format=json"
                search_data = self.session.get(search_url).json()
                results = search_data.get("query", {}).get("search", [])
                if not results: raise ValueError(f"No results for {query}")
                search_title = results[0]["title"].replace(' ', '_')
                url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(search_title)}"
                resp = self.session.get(url, timeout=10)
            
            data = resp.json()
            title = data.get("title", query)
            
            # 2. Extract and Clean Text
            extract = data.get("extract", "")
            
            return {
                "title": title,
                "url": f"https://en.wikipedia.org/wiki/{quote(search_title)}",
                "content": extract,
                "images": [{"url": data["thumbnail"]["url"], "caption": title}] if "thumbnail" in data else []
            }
        except Exception as e:
            logger.error(f"Wiki Error: {e}")
            raise