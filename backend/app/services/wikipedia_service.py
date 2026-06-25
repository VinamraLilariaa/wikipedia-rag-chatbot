import requests
import logging
import time
import re
import random
from bs4 import BeautifulSoup
from urllib.parse import quote, unquote

from backend.app.utils.logger import logger

WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKI_BASE = "https://en.wikipedia.org"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
]

SECTION_STOP_WORDS = ("references", "external links", "further reading", "notes", "see also")

class WikipediaService:
    def __init__(self):
        self.session = requests.Session()
        self._query_cache = {}

    def _get_headers(self):
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive"
        }

    def _request(self, params, timeout=10):
        for i in range(3):
            try:
                time.sleep(random.uniform(0.1, 0.4))
                resp = self.session.get(WIKI_API, params=params, headers=self._get_headers(), timeout=timeout)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                if i == 2: raise
                time.sleep(1)
        return None

    def search_article(self, query: str):
        params = {"action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": 5}
        data = self._request(params)
        results = data.get("query", {}).get("search", [])
        if not results: raise ValueError(f"No match for {query}")
        return {"title": results[0]["title"]}

    def get_article(self, query: str) -> dict:
        search_res = self.search_article(query)
        title = search_res["title"]
        
        params = {"action": "parse", "page": title, "format": "json", "prop": "text|images", "redirects": 1}
        data = self._request(params)
        soup = BeautifulSoup(data["parse"]["text"]["*"], "html.parser")
        
        # Images resolution
        images = []
        for img_name in data["parse"]["images"][:10]:
            if any(x in img_name.lower() for x in ('svg', 'icon', 'stub', 'edit')): continue
            img_params = {"action": "query", "titles": f"File:{img_name}", "prop": "imageinfo", "iiprop": "url", "format": "json"}
            try:
                img_data = self._request(img_params)
                pages = img_data.get("query", {}).get("pages", {})
                for pid in pages:
                    info = pages[pid].get("imageinfo", [{}])[0]
                    if info.get("url"): images.append({"url": info["url"], "caption": title})
            except: continue
            if len(images) >= 6: break

        return {
            "title": title,
            "url": f"{WIKI_BASE}/wiki/{quote(title.replace(' ', '_'))}",
            "content": self._extract_deep_content(soup),
            "images": images
        }

    def _extract_deep_content(self, soup: BeautifulSoup) -> str:
        # Clean
        for tag in soup.find_all(['style', 'script', 'aside']):
            tag.decompose()
        
        content = []
        curr_sec = "Main"
        for tag in soup.find_all(['p', 'h2', 'h3', 'table']):
            if tag.name in ('h2', 'h3'):
                h = tag.get_text(strip=True)
                if any(s in h.lower() for s in SECTION_STOP_WORDS): curr_sec = "Skip"
                else:
                    curr_sec = h
                    content.append(f"## {h}")
            elif curr_sec != "Skip":
                if tag.name == 'p':
                    t = tag.get_text(strip=True)
                    if len(t) > 40: content.append(f"[{curr_sec}] {t}")
                elif tag.name == 'table':
                    rows = tag.find_all("tr", limit=30)
                    for row in rows:
                        cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])[:8]]
                        if any(cells): content.append(f"[{curr_sec} Stats] " + " | ".join(cells))
        
        return "\n\n".join(content)[:80000]