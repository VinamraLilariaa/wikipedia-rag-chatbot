import requests
import logging
import time
import re
from bs4 import BeautifulSoup, SoupStrainer
from urllib.parse import quote, unquote
from spellchecker import SpellChecker
from rapidfuzz import fuzz

from backend.app.utils.logger import logger

WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKI_REST_API = "https://en.wikipedia.org/api/rest_v1"
WIKI_BASE = "https://en.wikipedia.org"

SECTION_STOP_WORDS = (
    "references", "external links", "further reading", 
    "notes", "see also", "citations", "bibliography", "records and statistics"
)

class WikipediaService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "WikiIntelBot/2.0 (Contact: team@example.com; Production Performance)",
            "Accept-Encoding": "gzip"
        })
        self._spell = SpellChecker()
        self._query_cache = {}

    def _request_with_retry(self, method, url, max_retries=3, timeout=10, **kwargs):
        for i in range(max_retries):
            try:
                response = self.session.request(method, url, timeout=timeout, **kwargs)
                if response.status_code == 429:
                    time.sleep(1)
                    continue
                response.raise_for_status()
                return response
            except Exception as e:
                if i == max_retries - 1: raise
                time.sleep(0.5)
        return None

    def search_article(self, query: str):
        clean_query = query.strip()
        params = {"action": "query", "list": "search", "srsearch": clean_query, "format": "json", "srlimit": 5}
        resp = self._request_with_retry("GET", WIKI_API, params=params).json()
        results = resp.get("query", {}).get("search", [])
        
        if not results:
            raise ValueError(f"No match for '{clean_query}'.")

        best_match = results[0]
        # Quick fuzzy check to avoid huge mismatches
        for res in results[:3]:
            if fuzz.token_sort_ratio(clean_query.lower(), res["title"].lower()) > 85:
                best_match = res
                break
        
        return {"title": best_match["title"]}

    def get_article(self, query: str) -> dict:
        search_result = self.search_article(query)
        title = search_result["title"]
        
        # Check cache first for huge articles
        if title in self._query_cache:
            return self._query_cache[title]
        
        try:
            # 1. FAST Summary (Critical for huge articles like Messi)
            summary_url = f"{WIKI_REST_API}/page/summary/{quote(title.replace(' ', '_'))}"
            summary_data = self._request_with_retry("GET", summary_url).json()
            summary = summary_data.get("extract", "")

            # 2. OPTIMIZED Full Content (using SoupStrainer for speed)
            html_url = f"{WIKI_REST_API}/page/html/{quote(title.replace(' ', '_'))}"
            html_resp = self._request_with_retry("GET", html_url, timeout=15)
            
            # LIGHTNING SCAN: Only parse paragraphs, headers, and tables
            strainer = SoupStrainer(['p', 'table', 'h2', 'h3'])
            soup = BeautifulSoup(html_resp.text, "lxml", parse_only=strainer)
            
            full_content = f"Summary: {summary}\n\n" + self._extract_content(soup)
            
            result = {
                "title": title,
                "url": f"{WIKI_BASE}/wiki/{quote(title.replace(' ', '_'))}",
                "content": full_content,
                "images": self._extract_images(soup, title),
            }
            self._query_cache[title] = result # Cache it!
            return result
        except Exception as e:
            logger.error(f"Scraper failed for {title}: {e}")
            raise

    def _extract_content(self, soup: BeautifulSoup) -> str:
        content = []
        current_section = "Main"
        
        # Process the strained elements directly
        elements = list(soup)
        for tag in elements[:800]: # LIMIT scanning to top 800 high-value elements
            if tag.name in ('h2', 'h3'):
                h = tag.get_text(strip=True)
                if any(s in h.lower() for s in SECTION_STOP_WORDS):
                    current_section = "Skip"
                else:
                    current_section = h
                    content.append(f"## {h}")
            elif current_section != "Skip":
                if tag.name == 'p':
                    t = tag.get_text(strip=True)
                    if len(t) > 40: content.append(f"[Section: {current_section}] {t}")
                elif tag.name == 'table':
                    # Only parse tables in career/info sections
                    if any(x in current_section.lower() for x in ('career', 'early', 'personal', 'stats')):
                        t = self._table_to_text(tag)
                        if t: content.append(f"[Section: {current_section} Info] {t}")
        
        return "\n\n".join(content)

    def _table_to_text(self, table) -> str:
        rows = table.find_all("tr", limit=20) # Limit rows for speed
        lines = []
        for row in rows:
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])[:6]]
            if any(cells): lines.append(" | ".join(cells))
        return "\n".join(lines)

    def _extract_images(self, soup: BeautifulSoup, title: str) -> list:
        images = []
        # Find first few large images
        for img_tag in soup.find_all("img", limit=20):
            src = img_tag.get("src", "")
            if not src or "svg" in src or "icon" in src.lower(): continue
            width = int(img_tag.get("width") or 0)
            if width > 150:
                images.append({"url": f"https:{src}", "caption": f"Image of {title}"})
            if len(images) >= 6: break
        return images