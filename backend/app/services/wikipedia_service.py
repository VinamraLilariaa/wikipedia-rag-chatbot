import requests
import logging
import time
import re
import random
from bs4 import BeautifulSoup
from urllib.parse import quote, unquote

from backend.app.utils.logger import logger

# Using the most stable human-mirror URL for scraping
WIKI_MIRROR = "https://en.wikipedia.org/wiki"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

class WikipediaService:
    def __init__(self):
        self.session = requests.Session()

    def get_article(self, query: str) -> dict:
        """
        The DEFINITIVE Scraper for HuggingFace.
        Uses direct URL resolution and robust HTML parsing.
        """
        # Clean title for URL
        clean_title = query.strip().replace(' ', '_')
        url = f"{WIKI_MIRROR}/{quote(clean_title)}"
        
        headers = {"User-Agent": random.choice(USER_AGENTS)}

        try:
            # 1. Fetch with broad tolerance
            resp = self.session.get(url, headers=headers, timeout=12, allow_redirects=True)
            
            # If the direct URL fails, try a search redirect
            if resp.status_code != 200:
                search_url = f"https://en.wikipedia.org/w/index.php?search={quote(query)}"
                resp = self.session.get(search_url, headers=headers, timeout=12, allow_redirects=True)
                if resp.status_code != 200:
                    raise ValueError(f"Wikipedia could not find '{query}'")

            soup = BeautifulSoup(resp.text, "html.parser")
            title = soup.find(id="firstHeading").get_text() if soup.find(id="firstHeading") else query
            
            # 2. Extract Data
            content = []
            body = soup.find(id="mw-content-text")
            if not body: raise ValueError("Empty article body")
            
            # Clean technical noise
            for tag in body.find_all(['style', 'script', 'aside', 'link', 'sup']):
                tag.decompose()

            # Process visible text
            for tag in body.find_all(['p', 'h2', 'h3', 'table']):
                if tag.name in ('h2', 'h3'):
                    h = tag.get_text().replace('[edit]', '').strip()
                    content.append(f"## {h}")
                elif tag.name == 'p':
                    t = tag.get_text().strip()
                    if len(t) > 30: content.append(t)
                elif tag.name == 'table':
                    rows = tag.find_all("tr", limit=15)
                    for row in rows:
                        cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])[:6]]
                        if any(cells): content.append(" | ".join(cells))

            # 3. Dynamic Image Capture
            images = []
            for img in body.find_all("img", limit=12):
                src = img.get("src", "")
                if src and "upload" in src and not any(x in src.lower() for x in ('svg', 'icon', 'stub', 'edit')):
                    images.append({"url": f"https:{src}", "caption": title})
                    if len(images) >= 6: break

            return {
                "title": title,
                "url": resp.url,
                "content": "\n\n".join(content)[:80000],
                "images": images
            }
        except Exception as e:
            logger.error(f"Scraper Final Audit Failure: {e}")
            raise