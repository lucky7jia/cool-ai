"""Plugin system for Expert Analyst - handles search and export plugins"""

import importlib.util
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel


class Plugin(ABC):
    """Base class for all plugins"""
    
    name: str
    description: str
    plugin_type: str  # "search" or "export"
    
    @abstractmethod
    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize the plugin with configuration"""
        pass
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """Execute the plugin's main functionality"""
        pass


class SearchPlugin(Plugin):
    """Base class for search plugins"""
    
    plugin_type = "search"
    
    @abstractmethod
    async def search(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """
        Search for information.
        
        Returns list of results with keys:
        - title: str
        - url: str
        - snippet: str
        - content: Optional[str]
        """
        pass
    
    async def execute(self, query: str, **kwargs) -> list[dict[str, Any]]:
        return await self.search(query, **kwargs)


class ExportPlugin(Plugin):
    """Base class for export plugins"""
    
    plugin_type = "export"
    
    @abstractmethod
    async def export(self, content: str, metadata: dict[str, Any]) -> str:
        """
        Export content to a specific format.
        
        Args:
            content: The analysis content to export
            metadata: Additional metadata (title, author, etc.)
        
        Returns:
            Formatted content string
        """
        pass
    
    async def execute(self, content: str, **kwargs) -> str:
        return await self.export(content, kwargs.get("metadata", {}))


class PluginInfo(BaseModel):
    """Plugin metadata"""
    name: str
    description: str
    plugin_type: str
    enabled: bool = True
    config: dict[str, Any] = {}


class PluginManager:
    """Manages loading and execution of plugins"""
    
    def __init__(self, plugins_dir: Path | str = "./plugins"):
        self.plugins_dir = Path(plugins_dir)
        self._plugins: dict[str, Plugin] = {}
        self._search_plugins: dict[str, SearchPlugin] = {}
        self._export_plugins: dict[str, ExportPlugin] = {}
    
    def register(self, plugin: Plugin) -> None:
        """Register a plugin instance"""
        self._plugins[plugin.name] = plugin
        
        if isinstance(plugin, SearchPlugin):
            self._search_plugins[plugin.name] = plugin
        elif isinstance(plugin, ExportPlugin):
            self._export_plugins[plugin.name] = plugin
    
    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get a plugin by name"""
        return self._plugins.get(name)
    
    def get_search_plugin(self, name: str) -> Optional[SearchPlugin]:
        """Get a search plugin by name"""
        return self._search_plugins.get(name)
    
    def get_export_plugin(self, name: str) -> Optional[ExportPlugin]:
        """Get an export plugin by name"""
        return self._export_plugins.get(name)
    
    def list_search_plugins(self) -> list[str]:
        """List all search plugin names"""
        return list(self._search_plugins.keys())
    
    def list_export_plugins(self) -> list[str]:
        """List all export plugin names"""
        return list(self._export_plugins.keys())
    
    async def search(
        self, 
        query: str, 
        engine: Optional[str] = None,
        max_results: int = 10
    ) -> list[dict[str, Any]]:
        """Execute a search using the specified or default engine"""
        if engine:
            plugin = self.get_search_plugin(engine)
            if not plugin:
                raise ValueError(f"Search plugin '{engine}' not found")
        else:
            # Use first available
            if not self._search_plugins:
                raise ValueError("No search plugins registered")
            plugin = next(iter(self._search_plugins.values()))
        
        return await plugin.search(query, max_results)
    
    async def export(
        self,
        content: str,
        format_name: str,
        metadata: Optional[dict[str, Any]] = None
    ) -> str:
        """Export content using the specified format"""
        plugin = self.get_export_plugin(format_name)
        if not plugin:
            raise ValueError(f"Export plugin '{format_name}' not found")
        
        return await plugin.export(content, metadata or {})


# Global plugin manager instance
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Get global plugin manager instance"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager
