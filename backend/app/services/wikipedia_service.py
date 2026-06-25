import requests
import logging
import time
import re
import random
from bs4 import BeautifulSoup
from urllib.parse import quote

from backend.app.utils.logger import logger

WIKI_URL_BASE = "https://en.wikipedia.org/wiki/"
SEARCH_URL_BASE = "https://en.wikipedia.org/w/index.php?search="

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

class WikipediaService:
    def __init__(self):
        self.session = requests.Session()

    def _get_headers(self):
        return {"User-Agent": random.choice(USER_AGENTS)}

    def get_article(self, query: str) -> dict:
        """
        The UNBLOCKABLE Scraper: Directly visits the Wikipedia website 
        to bypass all API limits and IP blocks.
        """
        # 1. SEARCH: If the query isn't a direct title, find it
        search_query = quote(query.strip().replace(' ', '+'))
        search_url = f"{SEARCH_URL_BASE}{search_query}"
        
        try:
            resp = self.session.get(search_url, headers=self._get_headers(), timeout=15)
            # If Wikipedia redirects us to the article page (common for famous names)
            final_url = resp.url
            title = unquote(final_url.split('/')[-1]).replace('_', ' ')
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # 2. EXTRACT CONTENT: Real HTML structure
            content = []
            curr_sec = "Summary"
            
            # Find all relevant content tags in the main body
            body = soup.find(id="mw-content-text")
            if not body: raise ValueError("Could not find article body")
            
            # Clean
            for tag in body.find_all(['style', 'script', 'aside', 'link']):
                tag.decompose()

            for tag in body.find_all(['p', 'h2', 'h3', 'table']):
                if tag.name in ('h2', 'h3'):
                    h = tag.get_text(strip=True).replace('[edit]', '')
                    curr_sec = h
                    content.append(f"## {h}")
                else:
                    if tag.name == 'p':
                        t = tag.get_text().strip()
                        if len(t) > 30: content.append(f"[{curr_sec}] {t}")
                    elif tag.name == 'table':
                        rows = tag.find_all("tr", limit=20)
                        for row in rows:
                            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])[:6]]
                            if any(cells): content.append(f"[{curr_sec} Stats] " + " | ".join(cells))

            # 3. IMAGES: High-quality thumbnails
            images = []
            for img_tag in body.find_all("img", limit=15):
                src = img_tag.get("src", "")
                if not src or "svg" in src or "icon" in src.lower(): continue
                images.append({"url": f"https:{src}", "caption": title})
                if len(images) >= 6: break

            return {
                "title": title,
                "url": final_url,
                "content": "\n\n".join(content)[:80000],
                "images": images
            }
        except Exception as e:
            logger.error(f"Scraper hard failure: {e}")
            raise