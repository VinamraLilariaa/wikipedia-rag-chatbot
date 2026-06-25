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

# OFFICIAL COMPLIANCE HEADERS
BOT_HEADERS = {
    "User-Agent": "WikipediaRAGResearcher/2.1 (tanav.research@example.com; Educational Research)",
    "Api-User-Agent": "WikipediaRAGResearcher/2.1"
}

SECTION_STOP_WORDS = ("references", "external links", "further reading", "notes", "see also")

class WikipediaService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(BOT_HEADERS)

    def _request(self, params, timeout=12):
        """Standardized polite request handler."""
        for i in range(3):
            try:
                # Polite 'human' delay
                time.sleep(random.uniform(0.3, 0.6))
                resp = self.session.get(WIKI_API, params=params, timeout=timeout)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                if i == 2: raise
                time.sleep(2)
        return None

    def search_article(self, query: str):
        params = {"action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": 3}
        data = self._request(params)
        results = data.get("query", {}).get("search", [])
        if not results: raise ValueError(f"No match for {query}")
        return {"title": results[0]["title"]}

    def get_article(self, query: str) -> dict:
        search_res = self.search_article(query)
        title = search_res["title"]
        
        # 1. BATCH PARSE (Text and image names in one hit)
        params = {"action": "parse", "page": title, "format": "json", "prop": "text|images", "redirects": 1}
        data = self._request(params)
        html = data["parse"]["text"]["*"]
        all_image_names = [img for img in data["parse"]["images"] if not any(x in img.lower() for x in ('svg', 'icon', 'stub', 'edit'))]
        
        # 2. BATCH IMAGE RESOLUTION (Single request for ALL urls)
        images = []
        if all_image_names:
            batch_names = "|".join([f"File:{i}" for i in all_image_names[:10]])
            img_params = {"action": "query", "titles": batch_names, "prop": "imageinfo", "iiprop": "url", "format": "json"}
            try:
                img_data = self._request(img_params)
                pages = img_data.get("query", {}).get("pages", {})
                for pid in pages:
                    info = pages[pid].get("imageinfo", [{}])[0]
                    if info.get("url"): images.append({"url": info["url"], "caption": title})
            except: pass

        return {
            "title": title,
            "url": f"{WIKI_BASE}/wiki/{quote(title.replace(' ', '_'))}",
            "content": self._extract_clean_content(BeautifulSoup(html, "html.parser")),
            "images": images[:6]
        }

    def _extract_clean_content(self, soup: BeautifulSoup) -> str:
        for tag in soup.find_all(['style', 'script', 'aside', 'link']):
            tag.decompose()
        
        content = []
        curr_sec = "Summary"
        for tag in soup.find_all(['p', 'h2', 'h3', 'table']):
            if tag.name in ('h2', 'h3'):
                h = tag.get_text(strip=True)
                curr_sec = "Skip" if any(s in h.lower() for s in SECTION_STOP_WORDS) else h
                if curr_sec != "Skip": content.append(f"## {h}")
            elif curr_sec != "Skip":
                if tag.name == 'p':
                    t = tag.get_text().strip()
                    if len(t) > 35: content.append(f"[{curr_sec}] {t}")
                elif tag.name == 'table':
                    rows = tag.find_all("tr", limit=25)
                    for row in rows:
                        cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])[:6]]
                        if any(cells): content.append(f"[{curr_sec} Data] " + " | ".join(cells))
        
        return "\n\n".join(content)[:80000]