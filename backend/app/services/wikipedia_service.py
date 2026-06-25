import requests
import logging
import time
import re
from urllib.parse import quote

from backend.app.utils.logger import logger

WIKI_REST_API = "https://en.wikipedia.org/api/rest_v1"
WIKI_BASE = "https://en.wikipedia.org"

class WikipediaService:
    def __init__(self):
        self.session = requests.Session()
        # Descriptive User-Agent for HuggingFace compliance
        self.session.headers.update({
            "User-Agent": "WikipediaRAGBot/2.0 (Contact: developer@huggingface.spaces; Research)",
            "Accept": "application/json"
        })

    def get_article(self, query: str) -> dict:
        """
        REST-API Express: Optimized for high-speed RAG and production stability.
        """
        # 1. Direct Summary Hit (Speed Priority)
        search_url = f"{WIKI_REST_API}/page/summary/{quote(query.strip().replace(' ', '_'))}"
        resp = self.session.get(search_url, timeout=10)
        
        if resp.status_code != 200:
            # Fallback to Action API search if direct REST hit misses
            search_api = "https://en.wikipedia.org/w/api.php"
            params = {"action": "query", "list": "search", "srsearch": query, "format": "json"}
            search_data = self.session.get(search_api, params=params).json()
            results = search_data.get("query", {}).get("search", [])
            if not results: raise ValueError(f"No result found for '{query}'")
            
            title = results[0]["title"]
            search_url = f"{WIKI_REST_API}/page/summary/{quote(title.replace(' ', '_'))}"
            resp = self.session.get(search_url, timeout=10)
            data = resp.json()
        else:
            data = resp.json()

        title = data.get("title", query)
        summary = data.get("extract", "")
        
        # 2. Fetch HTML for Deep Context Chunks
        html_url = f"{WIKI_REST_API}/page/html/{quote(title.replace(' ', '_'))}"
        # We use a longer timeout for HTML to ensure we get the full page
        html_resp = self.session.get(html_url, timeout=15)
        
        content = summary
        if html_resp.status_code == 200:
            # High-speed HTML text extraction
            content = re.sub(r'<[^>]+>', ' ', html_resp.text)
            content = re.sub(r'\s+', ' ', content).strip()

        return {
            "title": title,
            "url": f"{WIKI_BASE}/wiki/{quote(title.replace(' ', '_'))}",
            "summary": summary,
            "content": content[:60000], # Optimized context size for RAG stabilization
            "images": [{"url": data["thumbnail"]["url"], "caption": title}] if "thumbnail" in data else []
        }