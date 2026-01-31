"""Configuration management for Expert Analyst"""

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


class OllamaConfig(BaseModel):
    """Ollama model configuration"""
    base_url: str = "http://localhost:11434"
    model: str = "qwen2.5vl:7b"  # 本地视觉语言模型
    temperature: float = 0.7
    max_tokens: int = 4096
    enable_thinking: bool = True  # 开启思考模式


class SearchConfig(BaseModel):
    """Search configuration"""
    default_engine: str = "duckduckgo"
    tavily_api_key: Optional[str] = None
    max_results: int = 10


class ExportConfig(BaseModel):
    """Export configuration"""
    default_format: str = "markdown"
    output_dir: str = "./output"


class Config(BaseModel):
    """Main configuration"""
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)
    max_iterations: int = 3
    experts_dir: str = "./experts"
    plugins_dir: str = "./plugins"
    
    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """Load configuration from file or use defaults"""
        if config_path is None:
            # Check default locations
            locations = [
                Path.cwd() / "analyst.yaml",
                Path.home() / ".analyst" / "config.yaml",
            ]
            for loc in locations:
                if loc.exists():
                    config_path = loc
                    break
        
        if config_path and config_path.exists():
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}
            return cls(**data)
        
        return cls()
    
    def save(self, config_path: Optional[Path] = None) -> None:
        """Save configuration to file"""
        if config_path is None:
            config_path = Path.home() / ".analyst" / "config.yaml"
        
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False, allow_unicode=True)
        

# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global config instance"""
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def set_config(config: Config) -> None:
    """Set global config instance"""
    global _config
    _config = config
