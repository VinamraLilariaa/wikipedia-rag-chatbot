import requests
import random
import time
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)

class WikipediaService:
    def __init__(self):
        self.session = requests.Session()
        # High-trust headers to bypass data-center IP filtering
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/",
            "Origin": "https://www.google.com"
        }

    def get_article(self, query: str) -> dict:
        """
        INDUSTRIAL BYPASS: Uses high-trust headers and the Action API's 
        'Direct-Query' engine to bypass cloud IP blocks.
        """
        api_url = "https://en.wikipedia.org/w/api.php"
        
        # Step 1: The 'Polite' Search (Finds the exact official title)
        params_search = {
            "action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": 1
        }
        
        try:
            resp = self.session.get(api_url, params=params_search, headers=self.headers, timeout=12)
            data = resp.json()
            search_results = data.get("query", {}).get("search", [])
            
            if not search_results:
                # If search fails, try direct title match
                official_title = query
            else:
                official_title = search_results[0]["title"]

            # Step 2: The 'Industrial' Data Pull
            params_data = {
                "action": "query",
                "prop": "extracts|info|pageimages",
                "exintro": True,
                "explaintext": True,
                "titles": official_title,
                "format": "json",
                "inprop": "url",
                "pithumbsize": 500,
                "redirects": 1
            }
            
            resp_data = self.session.get(api_url, params=params_data, headers=self.headers, timeout=12)
            data_final = resp_data.json()
            pages = data_final.get("query", {}).get("pages", {})
            
            for pid in pages:
                p = pages[pid]
                if "extract" in p:
                    return {
                        "title": p["title"],
                        "url": p.get("fullurl", f"https://en.wikipedia.org/wiki/{quote(p['title'])}"),
                        "content": p["extract"],
                        "images": [{"url": p["thumbnail"]["source"], "caption": p["title"]}] if "thumbnail" in p else []
                    }
            
            raise ValueError(f"No specific content found for '{query}'")

        except Exception as e:
            logger.error(f"Industrial Bypass Internal Error: {e}")
            raise