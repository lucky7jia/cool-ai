"""Xiaohongshu (小红书) export plugin"""

from typing import Any
from datetime import datetime

from src.core.plugin import ExportPlugin


XHS_TEMPLATE = """🔥 {title}

{hook}

---

{main_points}

---

💡 核心观点：
{key_takeaway}

---

⚠️ 温馨提示：
投资有风险，本文仅供参考哦～

---

{tags}
"""


class XiaohongshuExportPlugin(ExportPlugin):
    """Export plugin for Xiaohongshu (小红书) format"""
    
    name = "xiaohongshu"
    description = "小红书笔记格式导出"
    
    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize the plugin"""
        pass
    
    async def export(self, content: str, metadata: dict[str, Any]) -> str:
        """
        Export content to Xiaohongshu format.
        
        Features:
        - Short, punchy sentences
        - Emojis throughout
        - Key points highlighted
        - Hashtags at the end
        """
        title = metadata.get("title", "专家分析")
        question = metadata.get("question", title)
        
        # Generate components
        hook = self._generate_hook(question)
        main_points = self._extract_main_points(content)
        key_takeaway = self._extract_key_takeaway(content)
        tags = self._generate_tags(question)
        
        return XHS_TEMPLATE.format(
            title=title[:20] + "..." if len(title) > 20 else title,
            hook=hook,
            main_points=main_points,
            key_takeaway=key_takeaway,
            tags=tags,
        )
    
    def _generate_hook(self, question: str) -> str:
        """Generate an attention-grabbing hook"""
        hooks = [
            f"很多人问我：{question}",
            f"关于「{question[:15]}...」这个问题，来看看专家怎么说！",
            f"今天来聊聊大家都关心的话题 👇",
        ]
        return hooks[0]
    
    def _extract_main_points(self, content: str) -> str:
        """Extract and format main points"""
        # Simplify content for XHS format
        points = []
        lines = content.split("\n")
        
        point_count = 0
        for line in lines:
            if line.strip().startswith("-") or line.strip().startswith("*"):
                if point_count < 5:
                    clean_line = line.strip().lstrip("-*").strip()
                    if len(clean_line) > 10:
                        emoji = ["📌", "💰", "📊", "🎯", "💡"][point_count % 5]
                        points.append(f"{emoji} {clean_line[:60]}...")
                        point_count += 1
        
        if not points:
            # Extract from paragraphs
            for line in lines:
                if len(line.strip()) > 30 and not line.startswith("#"):
                    if point_count < 4:
                        emoji = ["📌", "💰", "📊", "🎯"][point_count % 4]
                        points.append(f"{emoji} {line.strip()[:80]}...")
                        point_count += 1
        
        return "\n\n".join(points) if points else "详见完整分析报告～"
    
    def _extract_key_takeaway(self, content: str) -> str:
        """Extract the key takeaway"""
        # Look for conclusion section
        if "综合结论" in content:
            start = content.find("综合结论")
            end = content.find("##", start + 10)
            if end == -1:
                end = start + 200
            takeaway = content[start:end].strip()
            # Clean up
            takeaway = takeaway.replace("## 综合结论", "").replace("# 综合结论", "").strip()
            return takeaway[:150] + "..." if len(takeaway) > 150 else takeaway
        
        return "需要综合考虑多方因素，理性决策～"
    
    def _generate_tags(self, question: str) -> str:
        """Generate relevant hashtags"""
        base_tags = ["#投资理财", "#财经分析", "#AI分析"]
        
        # Add question-specific tags
        if "股票" in question or "股" in question:
            base_tags.extend(["#股票", "#A股"])
        if "楼市" in question or "房" in question:
            base_tags.extend(["#房产", "#楼市"])
        if "基金" in question:
            base_tags.extend(["#基金", "#定投"])
        
        return " ".join(base_tags[:6])
