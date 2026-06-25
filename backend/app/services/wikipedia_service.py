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
WIKI_BASE = "https://en.wikipedia.org"

# Headings under which we stop collecting body text - this is link/citation
# clutter, not article knowledge, and was previously being scraped in full.
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

# Wikimedia "chrome" images (project logos, edit icons, etc.) that show up
# inside article HTML but are never something a user wants to see.
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
    """
    Talks directly to the official Wikipedia API instead of scraping a
    search engine. This gives us three things for free:

      1. Typo-tolerant full text search (CirrusSearch), with an explicit
         "did you mean" suggestion we can surface to the user - this is
         what turns "Viart KOhli" into "Virat Kohli".
      2. Reliable article HTML (via action=parse) instead of fragile
         scraping of a rendered search-engine results page.
      3. A stable, ToS-friendly API instead of an undocumented scrape.
    """

    def __init__(self):
        self.session = requests.Session()

        # Production User-Agent: Specific, descriptive, and follows Wiki's "best practices"
        self.session.headers.update({
            "User-Agent": "WikipediaIntelligence/1.0 (https://github.com/vinamra26/wikipedia-rag-chatbot; production-rag-bot) requests-python",
            "Accept-Encoding": "gzip", 
        })

        # Used only for light, general-purpose word corrections (e.g. common
        # English typos). Proper-noun/name typos are instead resolved by
        # Wikipedia's own fuzzy search below, since a generic dictionary has
        # no idea who "Virat Kohli" is.
        self._spell = SpellChecker()

        # In-memory session cache for query -> title resolution.
        # This prevents redundant search API calls within the same server run.
        self._query_cache = {}

    def _request_with_retry(self, method, url, max_retries=3, **kwargs):
        """
        Helper to perform HTTP requests with exponential backoff on 429 errors.
        """
        for i in range(max_retries):
            try:
                response = self.session.request(method, url, **kwargs)
                
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                # If we get a 403 or 429, we wait much longer
                wait_time = (5 ** i) + 2  # 7s, 27s... much more aggressive backoff
                if i == max_retries - 1:
                    logger.error(f"Failed to fetch from Wikipedia after {max_retries} attempts: {e}")
                    raise
                
                logger.warning(f"Connection issue or rate limit. Retrying in {wait_time}s...")
                time.sleep(wait_time)
        
        raise Exception("Wikipedia is temporarily unavailable. Please try again in 30 seconds.")

    # -------------------------------------------------
    # Spelling correction
    # -------------------------------------------------

    def _correct_common_words(self, query: str) -> str:
        words = query.split()
        corrected = []
        changed = False

        for word in words:
            bare = re.sub(r"[^\w]", "", word)

            skip = (
                not bare
                or len(bare) <= 2
                or not bare.islower()
                or bare.isdigit()
                or bare.lower() in self._spell
            )

            if skip:
                corrected.append(word)
                continue

            suggestion = self._spell.correction(bare)

            if suggestion and suggestion != bare.lower():
                word = word.replace(bare, suggestion)
                changed = True

            corrected.append(word)

        result = " ".join(corrected)

        if changed:
            logger.info(f"Spell-corrected query words: '{query}' -> '{result}'")

        return result

    # -------------------------------------------------
    # Search
    # -------------------------------------------------

    def _wiki_search(self, query: str):
        """
        Uses Wikipedia's CirrusSearch to find the most relevant article.
        """
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

        results = []
        for res in search_results:
            results.append({"title": res["title"]})

        return results, suggestion
    def search_article(self, query: str):
        # 1. Check local cache first
        cache_key = query.lower().strip()
        if cache_key in self._query_cache:
            logger.info(f"Query cache hit: '{query}' -> '{self._query_cache[cache_key]['title']}'")
            return self._query_cache[cache_key]

        # 2. Correct common english words
        corrected = self._correct_common_words(query)

        # 3. Ask Wikipedia
        results, suggestion = self._wiki_search(corrected)

        if not results:
            # If no results, try the "did you mean" suggestion from Wiki if it exists
            # We strip any HTML tags from the suggestion (Wiki keeps them in search results)
            if suggestion:
                clean_suggestion = re.sub(r'<[^>]*>', '', suggestion)
                logger.info(f"Primary search failed, trying clean Wiki suggestion: '{clean_suggestion}'")
                results, _ = self._wiki_search(clean_suggestion)

            if not results:
                raise ValueError(f"No Wikipedia article found for '{query}'.")

        title = results[0]["title"]

        similarity = fuzz.token_sort_ratio(
            query.lower(),
            title.lower(),
        )

        result = {
            "title": title,
            "matched_query": title,
            "spelling_corrected": similarity < 92,
        }

        # Cache the result
        self._query_cache[cache_key] = result
        return result

    # -------------------------------------------------
    # Article fetching
    # -------------------------------------------------

    def _fetch_page_html(self, title: str) -> str:
        params = {
            "action": "parse",
            "page": title,
            "format": "json",
            "prop": "text",
            "redirects": 1,
        }

        response = self._request_with_retry("GET", WIKI_API, params=params, timeout=15)
        response.raise_for_status()

        data = response.json()

        if "error" in data:
            raise ValueError(f"Could not load Wikipedia page '{title}'.")

        return data["parse"]["text"]["*"]

    def get_article(self, query: str) -> dict:
        search_result = self.search_article(query)
        title = search_result["title"]

        logger.info(f"Resolved '{query}' -> Wikipedia article '{title}'")

        html = self._fetch_page_html(title)
        soup = BeautifulSoup(html, "html.parser")

        content = self._extract_content(soup)
        images = self._extract_images(soup, title)

        url = f"{WIKI_BASE}/wiki/{quote(title.replace(' ', '_'))}"

        return {
            "title": title,
            "url": url,
            "content": content,
            "images": images,
            "spelling_corrected": search_result["spelling_corrected"],
            "matched_query": search_result["matched_query"],
        }

    # -------------------------------------------------
    # Content extraction (text, lists, tables)
    # -------------------------------------------------

    def _extract_content(self, soup: BeautifulSoup) -> str:
        body = soup.find("div", class_="mw-parser-output")

        if not body:
            return ""

        content = []
        skip_section = False

        # We deliberately only walk direct children (recursive=False) so a
        # table's inner <p>/<li> tags don't ALSO get picked up separately
        # further down the tree, which would duplicate text.
        for tag in body.find_all(recursive=False):

            if tag.name in ("h2", "h3", "h4"):
                heading = re.sub(
                    r"\[\s*edit\s*\]", "", tag.get_text(" ", strip=True), flags=re.I
                ).strip()

                skip_section = any(
                    stop_word in heading.lower() for stop_word in SECTION_STOP_WORDS
                )

                if not skip_section and heading:
                    content.append(f"## {heading}")

                continue

            if skip_section:
                continue

            if tag.name == "p":
                text = tag.get_text(" ", strip=True)

                if len(text) > 20:
                    content.append(text)

            elif tag.name in ("ul", "ol"):
                for li in tag.find_all("li", recursive=False):
                    text = li.get_text(" ", strip=True)

                    if len(text) > 15:
                        content.append(f"- {text}")

            elif tag.name == "table":
                table_text = self._table_to_text(tag)

                if table_text:
                    content.append(table_text)

            elif tag.name == "div":
                # Quote boxes / galleries / some infobox wrappers nest
                # paragraphs and tables one level deeper than usual.
                for inner in tag.find_all(["p", "table"], recursive=False):

                    if inner.name == "p":
                        text = inner.get_text(" ", strip=True)

                        if len(text) > 20:
                            content.append(text)
                    else:
                        table_text = self._table_to_text(inner)

                        if table_text:
                            content.append(table_text)

        return "\n\n".join(content)

    def _table_to_text(self, table) -> str:
        """
        Converts a Wikipedia <table> into plain text.
        Handles infoboxes as key-value pairs and data tables as pipe-separated rows.
        """
        classes = table.get("class", []) or []
        is_infobox = any(c in classes for c in ["infobox", "vcard", "biota"])

        rows = table.find_all("tr")
        if not rows:
            return ""

        if is_infobox:
            caption = table.find("caption")
            label = caption.get_text(" ", strip=True) if caption else "Quick Facts"
            lines = [f"## {label}"]
            
            for row in rows:
                header = row.find("th")
                value = row.find("td")
                if header and value:
                    h_text = header.get_text(" ", strip=True)
                    v_text = value.get_text(" ", strip=True)
                    if h_text and v_text and len(h_text) < 50:
                        lines.append(f"{h_text}: {v_text}")
            return "\n".join(lines) if len(lines) > 1 else ""

        # Regular statistics or content table
        lines = []
        header_row = table.find("tr")
        if not header_row:
            return ""
            
        header_cells = [th.get_text(" ", strip=True) for th in header_row.find_all(["th", "td"])[:10]]
        if any(header_cells):
            lines.append(" | ".join(header_cells))
            lines.append("-" * 20)

        data_rows = rows[1:] if len(lines) > 0 else rows
        for row in data_rows[:100]: # Increased to 100 rows for deep career stats
            cells = [td.get_text(" ", strip=True) for td in row.find_all(["td", "th"])[:12]]
            if cells and any(cells):
                lines.append(" | ".join(cells))

        if len(lines) < 2:
            return ""
            
        table_title = ""
        prev_h = table.find_previous(["h2", "h3", "h4"])
        if prev_h:
            table_title = prev_h.get_text(" ", strip=True).split("[")[0].strip()

        header = f"Table: {table_title}\n" if table_title else "Data Table:\n"
        return header + "\n".join(lines)

    # -------------------------------------------------
    # Image extraction
    # -------------------------------------------------

    def _extract_images(self, soup: BeautifulSoup, title: str) -> list:
        images = []
        seen = set()

        for img in soup.find_all("img"):
            src = img.get("src", "")
            if not src:
                src = img.get("data-src", "")

            if not src:
                continue

            # Handle protocol-relative URLs
            if src.startswith("//"):
                full_url = "https:" + src
            elif src.startswith("http"):
                full_url = src
            else:
                continue

            # Only take official Wikipedia/Wikimedia uploads
            if "upload.wikimedia.org" not in full_url:
                continue

            # Skip "chrome" / UI images
            if any(pattern in full_url.lower() for pattern in SKIP_IMAGE_PATTERNS):
                continue

            width = img.get("width")
            try:
                if width and int(width) < 60:
                    continue
            except ValueError:
                pass

            # Remove forced upscaling. Using the original size Wikipedia provides 
            # ensures the URL is valid and the image actually exists.
            # (Previously was attempting to swap for /400px- which can fail)
            pass

            if full_url in seen:
                continue

            seen.add(full_url)

            caption = ""
            # Search for a caption in the surrounding figure/div
            figure = img.find_parent(["figure", "div", "td"])
            if figure:
                # Try common Wikipedia caption classes
                cap_tag = figure.find(class_=["thumbcaption", "infobox-caption", "wp-caption-text"])
                if cap_tag:
                    caption = cap_tag.get_text(" ", strip=True)

            images.append({"url": full_url, "caption": caption or title})

            if len(images) >= MAX_IMAGES:
                break

        return images