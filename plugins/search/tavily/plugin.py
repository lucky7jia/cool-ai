"""Tavily search plugin - AI-optimized search API"""

from typing import Any, Optional

from src.core.plugin import SearchPlugin


class TavilyPlugin(SearchPlugin):
    """Tavily AI search plugin"""
    
    name = "tavily"
    description = "AI 优化搜索引擎，每月 1000 次免费额度"
    
    def __init__(self):
        self._client = None
        self._api_key: Optional[str] = None
    
    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize the plugin with API key"""
        self._api_key = config.get("api_key")
        if self._api_key:
            try:
                from tavily import TavilyClient
                self._client = TavilyClient(api_key=self._api_key)
            except ImportError:
                print("Warning: tavily-python not installed")
    
    async def search(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """
        Search using Tavily AI search.
        
        Args:
            query: Search query
            max_results: Maximum number of results
        
        Returns:
            List of search results with title, url, snippet, and content
        """
        if not self._client:
            raise ValueError("Tavily client not initialized. Please provide API key.")
        
        results = []
        try:
            response = self._client.search(
                query=query,
                max_results=max_results,
                search_depth="advanced",  # More thorough search
                include_answer=True,
            )
            
            for r in response.get("results", []):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("content", "")[:500] if r.get("content") else "",
                    "content": r.get("content", ""),
                    "score": r.get("score", 0),
                })
            
            # Include the AI-generated answer if available
            if response.get("answer"):
                results.insert(0, {
                    "title": "Tavily AI 摘要",
                    "url": "",
                    "snippet": response["answer"],
                    "content": response["answer"],
                    "is_answer": True,
                })
        
        except Exception as e:
            print(f"Tavily search error: {e}")
        
        return results
