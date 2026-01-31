"""News article export plugin"""

from typing import Any
from datetime import datetime

from src.core.plugin import ExportPlugin


NEWS_TEMPLATE = """【{category}】{title}

{dateline}

{lead}

{body}

---

【分析来源】Expert Analyst AI 多专家协作分析系统

【免责声明】本文内容由人工智能生成，仅供参考，不构成投资建议。投资者应根据自身情况做出独立判断。

（完）
"""


class NewsExportPlugin(ExportPlugin):
    """Export plugin for news article format"""
    
    name = "news"
    description = "新闻稿格式导出"
    
    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize the plugin"""
        pass
    
    async def export(self, content: str, metadata: dict[str, Any]) -> str:
        """
        Export content to news article format.
        
        Features:
        - Professional news writing style
        - Inverted pyramid structure
        - Proper attribution
        """
        title = metadata.get("title", "专家分析报告")
        question = metadata.get("question", title)
        
        # Determine category
        category = self._determine_category(question)
        
        # Generate dateline
        now = datetime.now()
        dateline = f"北京，{now.year}年{now.month}月{now.day}日电"
        
        # Generate lead paragraph
        lead = self._generate_lead(question, content)
        
        # Process body
        body = self._process_body(content)
        
        return NEWS_TEMPLATE.format(
            category=category,
            title=self._generate_headline(question),
            dateline=dateline,
            lead=lead,
            body=body,
        )
    
    def _determine_category(self, question: str) -> str:
        """Determine the news category"""
        if any(word in question for word in ["股票", "股市", "A股", "基金"]):
            return "财经"
        elif any(word in question for word in ["楼市", "房产", "房价"]):
            return "房产"
        elif any(word in question for word in ["政策", "监管", "改革"]):
            return "政经"
        elif any(word in question for word in ["科技", "AI", "互联网"]):
            return "科技"
        else:
            return "财经"
    
    def _generate_headline(self, question: str) -> str:
        """Generate a news headline"""
        # Convert question to statement
        headline = question.replace("？", "").replace("?", "")
        headline = headline.replace("吗", "").replace("是否", "")
        
        if len(headline) > 30:
            headline = headline[:30] + "..."
        
        return f"多位专家分析：{headline}"
    
    def _generate_lead(self, question: str, content: str) -> str:
        """Generate the lead paragraph"""
        # Extract key conclusion
        conclusion = ""
        if "综合结论" in content:
            start = content.find("综合结论")
            end = content.find("\n\n", start)
            if end == -1:
                end = start + 300
            conclusion = content[start:end]
            conclusion = conclusion.replace("## 综合结论", "").replace("# 综合结论", "").strip()
        
        lead = f"针对「{question}」这一问题，Expert Analyst AI 分析系统汇集多位专家观点，"
        lead += f"经过多轮迭代分析后得出结论。"
        
        if conclusion:
            lead += f"\n\n专家组认为：{conclusion[:200]}..."
        
        return lead
    
    def _process_body(self, content: str) -> str:
        """Process content for news body"""
        # Remove markdown headers and format for news style
        lines = content.split("\n")
        result = []
        
        current_section = ""
        for line in lines:
            if line.startswith("# "):
                continue  # Skip main title
            elif line.startswith("## "):
                section_name = line.replace("## ", "").strip()
                current_section = f"\n**【{section_name}】**\n"
                result.append(current_section)
            elif line.startswith("### "):
                subsection = line.replace("### ", "").strip()
                result.append(f"\n{subsection}表示：")
            elif line.strip():
                result.append(line)
        
        return "\n".join(result)
