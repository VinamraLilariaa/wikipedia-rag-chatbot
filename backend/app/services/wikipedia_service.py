import requests
import re
import random
import time
from bs4 import BeautifulSoup
from urllib.parse import quote

# A set of human-like signatures to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

class WikipediaService:
    def __init__(self):
        self.session = requests.Session()

    def get_article(self, query: str) -> dict:
        """
        THE BATTERING RAM: Tries 4 different ways to reach Wikipedia.
        Designed specifically to bypass HuggingFace server blocks.
        """
        clean_query = query.strip()
        methods = [self._try_mobile_site, self._try_main_site, self._try_action_api, self._try_rest_api]
        
        last_error = "All connection methods failed."
        for method in methods:
            try:
                result = method(clean_query)
                if result and result.get("content"):
                    return result
            except Exception as e:
                last_error = str(e)
                continue
        
        raise ValueError(f"Wikipedia is unreachable on this server. Tried 4 protocols. Last error: {last_error}")

    def _try_mobile_site(self, query):
        """Method 1: The 'Mobile Mirror' (Highest Success Rate)"""
        url = f"https://en.m.wikipedia.org/wiki/{quote(query.replace(' ', '_'))}"
        resp = self.session.get(url, headers={"User-Agent": random.choice(USER_AGENTS)}, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            return {
                "title": query,
                "url": url,
                "content": soup.get_text()[:40000],
                "images": [] # Mobile images are harder to parse, prioritizing text
            }
        return None

    def _try_main_site(self, query):
        """Method 2: Direct Website Scraping"""
        url = f"https://en.wikipedia.org/wiki/{quote(query.replace(' ', '_'))}"
        resp = self.session.get(url, headers={"User-Agent": random.choice(USER_AGENTS)}, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            body = soup.find(id="mw-content-text")
            return {
                "title": query,
                "url": url,
                "content": body.get_text()[:40000] if body else soup.get_text()[:40000],
                "images": []
            }
        return None

    def _try_action_api(self, query):
        """Method 3: Official Action API"""
        api_url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query", "prop": "extracts|info|pageimages", "exintro": True, 
            "explaintext": True, "titles": query, "format": "json", "inprop": "url", "redirects": 1
        }
        resp = self.session.get(api_url, params=params, headers={"User-Agent": random.choice(USER_AGENTS)}, timeout=10)
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        for pid in pages:
            p = pages[pid]
            if "extract" in p:
                return {
                    "title": p["title"], "url": p["fullurl"], "content": p["extract"],
                    "images": [{"url": p["thumbnail"]["source"], "caption": p["title"]}] if "thumbnail" in p else []
                }
        return None

    def _try_rest_api(self, query):
        """Method 4: REST API (Final Backup)"""
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(query.replace(' ', '_'))}"
        resp = self.session.get(url, headers={"User-Agent": random.choice(USER_AGENTS)}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "title": data["title"], "url": data["content_urls"]["desktop"]["page"],
                "content": data["extract"], "images": []
            }
        return None