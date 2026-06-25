import requests
import logging
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import quote, unquote
from spellchecker import SpellChecker
from rapidfuzz import fuzz

from backend.app.utils.logger import logger

WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKI_REST_API = "https://en.wikipedia.org/api/rest_v1"
WIKI_BASE = "https://en.wikipedia.org"

SECTION_STOP_WORDS = (
    "references", "external links", "further reading", 
    "notes", "see also", "citations", "bibliography"
)

class WikipediaService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "WikipediaIntelligenceBot/1.0 (Contact: team@example.com; RAG Project)",
            "Accept-Encoding": "gzip"
        })
        self._spell = SpellChecker()
        self._query_cache = {}

    def _request_with_retry(self, method, url, max_retries=5, **kwargs):
        for i in range(max_retries):
            try:
                response = self.session.request(method, url, **kwargs)
                if response.status_code == 429:
                    time.sleep((5 ** i) + 2)
                    continue
                response.raise_for_status()
                return response
            except Exception as e:
                if i == max_retries - 1: raise
                time.sleep(2 ** i)
        return None

    def search_article(self, query: str):
        clean_query = query.strip()
        queries_to_try = [clean_query]
        
        # Simple spell correction
        words = clean_query.split()
        if len(words) < 4:
            corrected = " ".join([self._spell.correction(w) or w for w in words])
            if corrected.lower() != clean_query.lower():
                queries_to_try.append(corrected)

        search_results = []
        for q in queries_to_try:
            params = {"action": "query", "list": "search", "srsearch": q, "format": "json", "srlimit": 5}
            resp = self._request_with_retry("GET", WIKI_API, params=params).json()
            results = resp.get("query", {}).get("search", [])
            if results:
                search_results.extend(results)
                break
        
        if not search_results:
            raise ValueError(f"No match for '{clean_query}'.")

        best_match = search_results[0]
        highest_score = 0
        for res in search_results[:3]:
            score = fuzz.token_sort_ratio(clean_query.lower(), res["title"].lower())
            if "list of" in res["title"].lower(): score -= 20
            if score > highest_score:
                highest_score = score
                best_match = res

        return {
            "title": best_match["title"],
            "matched_query": best_match["title"],
            "spelling_corrected": highest_score < 85
        }

    def get_article(self, query: str) -> dict:
        search_result = self.search_article(query)
        title = search_result["title"]
        
        try:
            # 1. Fetch Official Summary (Highly Reliable)
            summary_url = f"{WIKI_REST_API}/page/summary/{quote(title.replace(' ', '_'))}"
            summary_data = self._request_with_retry("GET", summary_url).json()
            summary = summary_data.get("extract", "")

            # 2. Fetch Full HTML
            html_url = f"{WIKI_REST_API}/page/html/{quote(title.replace(' ', '_'))}"
            html_resp = self._request_with_retry("GET", html_url)
            soup = BeautifulSoup(html_resp.text, "html.parser")
            
            # Combine Summary + Deep Content
            full_content = f"Summary: {summary}\n\n" + self._extract_content(soup)
            
            return {
                "title": title,
                "url": f"{WIKI_BASE}/wiki/{quote(title.replace(' ', '_'))}",
                "content": full_content,
                "images": self._extract_images(soup, title),
                "spelling_corrected": search_result["spelling_corrected"],
                "matched_query": search_result["matched_query"],
            }
        except Exception as e:
            logger.error(f"REST API failed for {title}: {e}")
            return self._get_article_fallback(title, search_result)

    def _get_article_fallback(self, title: str, meta: dict) -> dict:
        params = {"action": "parse", "page": title, "format": "json", "prop": "text", "redirects": 1}
        resp = self._request_with_retry("GET", WIKI_API, params=params).json()
        html = resp["parse"]["text"]["*"]
        soup = BeautifulSoup(html, "html.parser")
        return {
            "title": title,
            "url": f"{WIKI_BASE}/wiki/{quote(title.replace(' ', '_'))}",
            "content": self._extract_content(soup),
            "images": self._extract_images(soup, title),
            "spelling_corrected": meta["spelling_corrected"],
            "matched_query": meta["matched_query"],
        }

    def _extract_content(self, soup: BeautifulSoup) -> str:
        content = []
        current_section = "Main"
        
        # Deep search: find all paragraphs, tables and headers anywhere in the document
        # This bypasses the <section> tag nesting issue in the REST API
        for tag in soup.find_all(['p', 'table', 'h2', 'h3']):
            if tag.name in ('h2', 'h3'):
                h = tag.get_text(" ", strip=True)
                if any(s in h.lower() for s in SECTION_STOP_WORDS):
                    current_section = "Skip"
                else:
                    current_section = h
                    content.append(f"## {h}")
            elif current_section != "Skip":
                if tag.name == 'p':
                    t = tag.get_text(" ", strip=True)
                    if len(t) > 30: content.append(f"[Section: {current_section}] {t}")
                elif tag.name == 'table':
                    t = self._table_to_text(tag)
                    if t: content.append(f"[Section: {current_section} Stats] {t}")
        
        return "\n\n".join(content)

    def _table_to_text(self, table) -> str:
        rows = table.find_all("tr")
        if len(rows) < 2: return ""
        lines = []
        for row in rows[:50]:
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])[:10]]
            if any(cells): lines.append(" | ".join(cells))
        return "\n".join(lines)

    def _extract_images(self, soup: BeautifulSoup, title: str) -> list:
        images = []
        # Infoboxes in REST API use <figure> or special classes
        for img_tag in soup.find_all("img"):
            src = img_tag.get("src", "")
            if not src or "svg" in src or "icon" in src.lower() or "Static" in src: continue
            width = int(img_tag.get("width") or 0)
            if width > 120:
                images.append({"url": f"https:{src}", "caption": f"Wikipedia image: {title}"})
            if len(images) >= 6: break
        return images