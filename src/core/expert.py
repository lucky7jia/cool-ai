"""Expert definition and loader - parses EXPERT.md files"""

import json
import re
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field


class ExpertMetadata(BaseModel):
    """Metadata for an expert"""
    emoji: str = "🤖"
    priority: int = 1
    domains: list[str] = Field(default_factory=list)
    

class Expert(BaseModel):
    """Expert definition parsed from EXPERT.md"""
    name: str
    description: str
    metadata: ExpertMetadata = Field(default_factory=ExpertMetadata)
    system_prompt: str  # The markdown content after frontmatter
    source_path: Optional[Path] = None
    
    class Config:
        arbitrary_types_allowed = True
    
    def matches_query(self, query: str) -> bool:
        """Check if this expert is relevant to the query based on domains"""
        query_lower = query.lower()
        # Check if any domain keyword is in the query
        for domain in self.metadata.domains:
            if domain.lower() in query_lower:
                return True
        # Also check description
        for word in self.description.lower().split():
            if len(word) > 3 and word in query_lower:
                return True
        return False
    
    def get_display_name(self) -> str:
        """Get display name with emoji"""
        return f"{self.metadata.emoji} {self.name}"


class ExpertLoader:
    """Loads experts from EXPERT.md files"""
    
    FRONTMATTER_PATTERN = re.compile(
        r'^---\s*\n(.*?)\n---\s*\n(.*)$',
        re.DOTALL
    )
    
    def __init__(self, experts_dir: Path | str = "./experts"):
        self.experts_dir = Path(experts_dir)
        self._cache: dict[str, Expert] = {}
    
    def parse_expert_file(self, file_path: Path) -> Expert:
        """Parse a single EXPERT.md file"""
        content = file_path.read_text(encoding="utf-8")
        
        match = self.FRONTMATTER_PATTERN.match(content)
        if not match:
            raise ValueError(f"Invalid EXPERT.md format in {file_path}: missing frontmatter")
        
        frontmatter_str = match.group(1)
        body = match.group(2).strip()
        
        # Parse YAML frontmatter
        frontmatter = yaml.safe_load(frontmatter_str)
        if not frontmatter:
            raise ValueError(f"Empty frontmatter in {file_path}")
        
        # Extract required fields
        name = frontmatter.get("name")
        description = frontmatter.get("description", "")
        
        if not name:
            raise ValueError(f"Missing 'name' in frontmatter of {file_path}")
        
        # Parse metadata (can be JSON string or dict)
        metadata_raw = frontmatter.get("metadata", {})
        if isinstance(metadata_raw, str):
            metadata_raw = json.loads(metadata_raw)
        
        metadata = ExpertMetadata(**metadata_raw)
        
        return Expert(
            name=name,
            description=description,
            metadata=metadata,
            system_prompt=body,
            source_path=file_path,
        )
    
    def load_all(self, reload: bool = False) -> list[Expert]:
        """Load all experts from the experts directory"""
        if self._cache and not reload:
            return list(self._cache.values())
        
        self._cache.clear()
        experts = []
        
        if not self.experts_dir.exists():
            return experts
        
        # Look for EXPERT.md in subdirectories
        for expert_dir in self.experts_dir.iterdir():
            if not expert_dir.is_dir():
                continue
            
            expert_file = expert_dir / "EXPERT.md"
            if not expert_file.exists():
                continue
            
            try:
                expert = self.parse_expert_file(expert_file)
                self._cache[expert.name] = expert
                experts.append(expert)
            except Exception as e:
                print(f"Warning: Failed to load {expert_file}: {e}")
        
        # Sort by priority
        experts.sort(key=lambda x: x.metadata.priority)
        return experts
    
    def get_expert(self, name: str) -> Optional[Expert]:
        """Get a specific expert by name"""
        if not self._cache:
            self.load_all()
        return self._cache.get(name)
    
    def find_relevant_experts(self, query: str, max_experts: int = 4) -> list[Expert]:
        """Find experts relevant to a query"""
        all_experts = self.load_all()
        
        # Score each expert
        scored = []
        for expert in all_experts:
            if expert.matches_query(query):
                scored.append((expert, expert.metadata.priority))
            else:
                # Still include with lower priority
                scored.append((expert, expert.metadata.priority + 100))
        
        # Sort by score and return top N
        scored.sort(key=lambda x: x[1])
        return [e for e, _ in scored[:max_experts]]
