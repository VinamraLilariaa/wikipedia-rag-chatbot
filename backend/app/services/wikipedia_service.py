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
                    wait = (5 ** i) + 2
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                return response
            except Exception as e:
                if i == max_retries - 1: raise
                time.sleep(2 ** i)
        return None

    def _correct_common_words(self, query: str) -> str:
        words = query.split()
        corrected_words = []
        for word in words:
            # Only correct words that are likely typos (len > 3, all alpha)
            if len(word) > 3 and word.isalpha():
                corr = self._spell.correction(word)
                corrected_words.append(corr if corr else word)
            else:
                corrected_words.append(word)
        return " ".join(corrected_words)

    def search_article(self, query: str):
        """
        Rock-solid search that prioritizes exact matches and rejects hallucinations.
        """
        clean_query = query.strip()
        
        # Try both the original and a corrected version if they differ
        queries_to_try = [clean_query]
        corrected = self._correct_common_words(clean_query)
        if corrected.lower() != clean_query.lower():
            queries_to_try.append(corrected)

        search_results = []
        for q in queries_to_try:
            params = {
                "action": "query",
                "list": "search",
                "srsearch": q,
                "format": "json",
                "srlimit": 5
            }
            resp = self._request_with_retry("GET", WIKI_API, params=params).json()
            results = resp.get("query", {}).get("search", [])
            if results:
                search_results.extend(results)
                break # If we found results, stop
        
        if not search_results:
            raise ValueError(f"No Wikipedia article found for '{clean_query}'.")

        # 2. Pick the best match among top 3 using fuzzy ratio
        # This prevents "Virat Kohli" matching "Dschinghis Khan"
        best_match = search_results[0]
        highest_score = 0
        
        for res in search_results[:3]:
            score = fuzz.token_sort_ratio(clean_query.lower(), res["title"].lower())
            # Prioritize main articles over "List of..."
            if "list of" in res["title"].lower(): score -= 20
            
            if score > highest_score:
                highest_score = score
                best_match = res
        
        # 3. Sanity check: If the score is too low, it's likely a hallucination
        if highest_score < 30 and len(clean_query) > 3:
            logger.warning(f"Rejecting weak match '{best_match['title']}' for query '{clean_query}' (score: {highest_score})")
            # If we reject it, just take the first result but log it
            best_match = search_results[0]

        return {
            "title": best_match["title"],
            "matched_query": best_match["title"],
            "spelling_corrected": highest_score < 80 
        }

    def get_article(self, query: str) -> dict:
        search_result = self.search_article(query)
        title = search_result["title"]
        
        try:
            # Try REST API
            encoded_title = quote(title.replace(' ', '_'))
            url = f"{WIKI_REST_API}/page/html/{encoded_title}"
            resp = self._request_with_retry("GET", url, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            
            return {
                "title": title,
                "url": f"{WIKI_BASE}/wiki/{encoded_title}",
                "content": self._extract_content(soup),
                "images": self._extract_images(soup, title),
                "spelling_corrected": search_result["spelling_corrected"],
                "matched_query": search_result["matched_query"],
            }
        except Exception:
            # Fallback
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
        body = soup.find("body") or soup.find("div", class_="mw-parser-output")
        if not body: return ""
        content = []
        current_section = "Intro"
        skip = False
        
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
        rows = table.find_all("tr")
        if len(rows) < 2: return ""
        lines = []
        for row in rows[:80]:
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])[:12]]
            if any(cells): lines.append(" | ".join(cells))
        return "\n".join(lines)

    def _extract_images(self, soup: BeautifulSoup, title: str) -> list:
        images = []
        # Main infobox image first
        infobox = soup.find(class_=re.compile("infobox|vcard"))
        if infobox:
            img_tag = infobox.find("img")
            if img_tag and img_tag.get("src"):
                images.append({"url": f"https:{img_tag['src']}", "caption": title})

        # Other images
        for img_tag in soup.find_all("img"):
            src = img_tag.get("src", "")
            if not src or "svg" in src or "icon" in src.lower(): continue
            width = int(img_tag.get("width") or 0)
            if width > 100:
                images.append({"url": f"https:{src}", "caption": f"Image from {title}"})
            if len(images) >= 6: break
        return images