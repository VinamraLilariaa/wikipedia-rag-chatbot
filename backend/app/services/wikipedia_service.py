import re
import time
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz
from spellchecker import SpellChecker

from backend.app.config.settings import MAX_IMAGES
from backend.app.utils.logger import logger

WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKI_REST_API = "https://en.wikipedia.org/api/rest_v1"
WIKI_BASE = "https://en.wikipedia.org"

SECTION_STOP_WORDS = (
    "references",
    "external links",
    "see also",
    "further reading",
    "notes",
    "bibliography",
    "citations",
    "sources",
)

SKIP_IMAGE_PATTERNS = (
    "wiktionary",
    "commons-logo",
    "edit-clear",
    "question_book",
    "ambox",
    "padlock",
    "wikiquote",
    "wikisource",
    "sister_projects",
    "icons8",
    "loudspeaker",
    "disambig",
)


class WikipediaService:

    def __init__(self):
        self.session = requests.Session()
        # Production headers to avoid data-center blocking
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
                    # Aggressive backoff for rate limits
                    wait = (5 ** i) + 2
                    logger.warning(f"Rate limited. Waiting {wait}s...")
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                return response
            except Exception as e:
                if i == max_retries - 1:
                    logger.error(f"Final retry failed: {e}")
                    raise
                time.sleep(2 ** i)
        return None

    def _correct_common_words(self, query: str) -> str:
        words = query.split()
        corrected = []
        for word in words:
            bare = re.sub(r"[^\w]", "", word)
            if not bare or not bare.islower() or bare.lower() in self._spell:
                corrected.append(word)
                continue
            suggestion = self._spell.correction(bare)
            corrected.append(word.replace(bare, suggestion) if suggestion else word)
        return " ".join(corrected)

    def _wiki_search(self, query: str):
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 5,
            "srinfo": "suggestion",
            "srprop": "",
        }
        response = self._request_with_retry("GET", WIKI_API, params=params, timeout=10)
        data = response.json()
        search_results = data.get("query", {}).get("search", [])
        suggestion = data.get("query", {}).get("searchinfo", {}).get("suggestion")
        results = [{"title": res["title"]} for res in search_results]
        return results, suggestion

    def search_article(self, query: str):
        cache_key = query.lower().strip()
        if cache_key in self._query_cache:
            return self._query_cache[cache_key]

        results, suggestion = self._wiki_search(self._correct_common_words(query))

        if not results and suggestion:
            results, _ = self._wiki_search(re.sub(r'<[^>]*>', '', suggestion))

        if not results:
            raise ValueError(f"No Wikipedia article found for '{query}'.")

        title = results[0]["title"]
        result = {
            "title": title,
            "matched_query": title,
            "spelling_corrected": fuzz.token_sort_ratio(query.lower(), title.lower()) < 92,
        }
        self._query_cache[cache_key] = result
        return result

    def _fetch_page_html(self, title: str) -> str:
        # Modern REST API for cleaner HTML and better performance
        encoded_title = quote(title.replace(' ', '_'))
        url = f"{WIKI_REST_API}/page/html/{encoded_title}"
        response = self._request_with_retry("GET", url, timeout=15)
        return response.text

    def get_article(self, query: str) -> dict:
        search_result = self.search_article(query)
        title = search_result["title"]
        
        try:
            html = self._fetch_page_html(title)
            soup = BeautifulSoup(html, "html.parser")
            
            # Use REST API for images as well if possible (metadata endpoint)
            metadata_url = f"{WIKI_REST_API}/page/metadata/{quote(title.replace(' ', '_'))}"
            metadata_resp = self.session.get(metadata_url, timeout=5)
            
            return {
                "title": title,
                "url": f"{WIKI_BASE}/wiki/{quote(title.replace(' ', '_'))}",
                "content": self._extract_content(soup),
                "images": self._extract_images(soup, title),
                "spelling_corrected": search_result["spelling_corrected"],
                "matched_query": search_result["matched_query"],
            }
        except Exception as e:
            logger.error(f"Failed to fetch from REST API: {e}")
            # Fallback to action API if REST fails
            return self._get_article_fallback(title, search_result)

    def _get_article_fallback(self, title: str, search_meta: dict) -> dict:
        params = {"action": "parse", "page": title, "format": "json", "prop": "text", "redirects": 1}
        response = self._request_with_retry("GET", WIKI_API, params=params, timeout=15)
        data = response.json()
        html = data["parse"]["text"]["*"]
        soup = BeautifulSoup(html, "html.parser")
        return {
            "title": title,
            "url": f"{WIKI_BASE}/wiki/{quote(title.replace(' ', '_'))}",
            "content": self._extract_content(soup),
            "images": self._extract_images(soup, title),
            "spelling_corrected": search_meta["spelling_corrected"],
            "matched_query": search_meta["matched_query"],
        }

    def _extract_content(self, soup: BeautifulSoup) -> str:
        body = soup.find("div", class_="mw-parser-output")
        if not body: return ""
        content = []
        skip = False
        # Attach the section heading to the content to help retrieval
        current_section = "Intro"
        for tag in body.find_all(recursive=False):
            if tag.name in ("h2", "h3"):
                h = tag.get_text(" ", strip=True)
                skip = any(s in h.lower() for s in SECTION_STOP_WORDS)
                if not skip: 
                    current_section = h
                    content.append(f"## {h}")
            elif not skip:
                if tag.name == "p":
                    t = tag.get_text(" ", strip=True)
                    if len(t) > 20: content.append(f"[Section: {current_section}] {t}")
                elif tag.name == "table":
                    t = self._table_to_text(tag)
                    if t: content.append(f"[Section: {current_section} Table] {t}")
        return "\n\n".join(content)

    def _table_to_text(self, table) -> str:
        classes = table.get("class", []) or []
        is_info = any(c in classes for c in ["infobox", "vcard"])
        rows = table.find_all("tr")
        if not rows: return ""
        if is_info:
            lines = []
            for row in rows:
                th, td = row.find("th"), row.find("td")
                if th and td:
                    lines.append(f"{th.get_text(strip=True)}: {td.get_text(strip=True)}")
            return "\n".join(lines)
        lines = []
        for row in rows[:80]: # Deep table support for production stats
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])[:12]]
            if any(cells): lines.append(" | ".join(cells))
        return "\n".join(lines)

    def _extract_images(self, soup: BeautifulSoup, title: str) -> list:
        images = []
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if not src.startswith("//") and not src.startswith("http"): continue
            url = "https:" + src if src.startswith("//") else src
            if "upload.wikimedia.org" not in url or any(p in url.lower() for p in SKIP_IMAGE_PATTERNS): continue
            images.append({"url": url, "caption": title})
            if len(images) >= MAX_IMAGES: break
        return images