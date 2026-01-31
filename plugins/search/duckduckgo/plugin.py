"""Web search plugin - uses Sogou as primary search engine for Chinese content"""

from typing import Any
import httpx
import re
import urllib.parse

from src.core.plugin import SearchPlugin


class DuckDuckGoPlugin(SearchPlugin):
    """Web search plugin using Sogou (best for Chinese content)"""
    
    name = "duckduckgo"
    description = "网页搜索引擎 (搜狗)"
    
    def __init__(self):
        self._client: httpx.AsyncClient | None = None
    
    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize the plugin"""
        pass
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=15,
                verify=False,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                }
            )
        return self._client
    
    async def search(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """
        Search the web using Sogou.
        
        Args:
            query: Search query
            max_results: Maximum number of results
        
        Returns:
            List of search results with title, url, snippet
        """
        try:
            results = await self._search_sogou(query, max_results)
            if results:
                return results
        except Exception as e:
            print(f"Sogou search error: {e}")
        
        return []
    
    async def _search_sogou(self, query: str, max_results: int) -> list[dict[str, Any]]:
        """Search using Sogou"""
        client = await self._get_client()
        
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.sogou.com/web?query={encoded_query}"
        
        resp = await client.get(url)
        html = resp.text
        
        return self._parse_sogou_html(html, max_results)
    
    def _parse_sogou_html(self, html: str, max_results: int) -> list[dict[str, Any]]:
        """Parse Sogou search results HTML"""
        results = []
        
        # Sogou result pattern - look for h3 with links
        # Pattern 1: h3 > a
        pattern1 = r'<h3[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?</h3>'
        matches = re.findall(pattern1, html, re.DOTALL)
        
        for sogou_url, title in matches[:max_results]:
            try:
                # Clean title
                title = re.sub(r'<[^>]+>', '', title).strip()
                title = re.sub(r'\s+', ' ', title)
                
                if not title or len(title) < 3:
                    continue
                
                # Sogou uses redirect URLs, extract the real URL if possible
                # The redirect format is /link?url=...
                real_url = sogou_url
                if '/link?url=' in sogou_url:
                    # Keep the sogou URL as is - it will redirect
                    real_url = f"https://www.sogou.com{sogou_url}" if sogou_url.startswith('/') else sogou_url
                
                # Find snippet - look for nearby text
                snippet = ""
                # Look for description after the h3
                snippet_pattern = r'<p[^>]*class="[^"]*str[^"]*"[^>]*>(.*?)</p>'
                snippet_matches = re.findall(snippet_pattern, html, re.DOTALL)
                if snippet_matches and len(results) < len(snippet_matches):
                    snippet = re.sub(r'<[^>]+>', '', snippet_matches[len(results)]).strip()
                
                results.append({
                    "title": title[:100],
                    "url": real_url,
                    "snippet": snippet[:300] if snippet else f"来源: 搜狗搜索",
                })
            except Exception:
                continue
        
        return results
    
    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
