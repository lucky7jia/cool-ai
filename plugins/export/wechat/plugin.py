"""WeChat (公众号) export plugin"""

from typing import Any
from datetime import datetime

from src.core.plugin import ExportPlugin


WECHAT_TEMPLATE = """# {title}

> 💡 本文由 AI 专家分析助手生成，仅供参考，不构成投资建议。

---

{content}

---

## 📌 关于本文

本分析报告由多位 AI 专家协作完成，通过迭代自证机制确保分析质量。

**生成时间**: {date}

**免责声明**: 本文内容仅供参考，不构成任何投资建议。投资有风险，入市需谨慎。

---

*喜欢这篇分析？欢迎关注我们获取更多专业分析！*
"""


class WeChatExportPlugin(ExportPlugin):
    """Export plugin for WeChat (公众号) format"""
    
    name = "wechat"
    description = "公众号文章格式导出"
    
    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize the plugin"""
        pass
    
    async def export(self, content: str, metadata: dict[str, Any]) -> str:
        """
        Export content to WeChat format.
        
        Features:
        - Long-form article format
        - Proper section headers
        - Disclaimer and footer
        """
        title = metadata.get("title", "专家分析报告")
        date = datetime.now().strftime("%Y年%m月%d日")
        
        # Process content for WeChat
        # - Convert headers to proper format
        # - Add blockquotes for key points
        processed_content = self._process_content(content)
        
        return WECHAT_TEMPLATE.format(
            title=title,
            content=processed_content,
            date=date,
        )
    
    def _process_content(self, content: str) -> str:
        """Process content for WeChat format"""
        lines = content.split("\n")
        result = []
        
        for line in lines:
            # Emphasize key headers
            if line.startswith("## 综合结论"):
                result.append("## 🎯 综合结论")
            elif line.startswith("## 专家分析"):
                result.append("## 👨‍💼 专家分析")
            elif line.startswith("## 参考资料"):
                result.append("## 📚 参考资料")
            elif line.startswith("### "):
                # Add emoji to expert sections
                result.append(line)
            else:
                result.append(line)
        
        return "\n".join(result)
