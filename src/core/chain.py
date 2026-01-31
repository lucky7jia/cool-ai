"""Analysis chain - orchestrates the multi-expert analysis process"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime

from .expert import Expert, ExpertLoader
from .llm import get_llm_manager, LLMManager
from .plugin import get_plugin_manager, PluginManager

# Import stock data plugin
try:
    from plugins.data.stock import get_stock_context
    HAS_STOCK_PLUGIN = True
except ImportError:
    HAS_STOCK_PLUGIN = False
    async def get_stock_context(query: str) -> str:
        return ""


@dataclass
class SearchResult:
    """A single search result"""
    title: str
    url: str
    snippet: str
    content: Optional[str] = None


@dataclass
class ExpertAnalysis:
    """Analysis from a single expert"""
    expert_name: str
    expert_emoji: str
    analysis: str
    key_points: list[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Complete analysis result"""
    question: str
    search_results: list[SearchResult]
    expert_analyses: list[ExpertAnalysis]
    consensus: str
    iteration_count: int
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_markdown(self) -> str:
        """Convert result to markdown format"""
        lines = [
            f"# 分析报告",
            f"",
            f"**问题**: {self.question}",
            f"",
            f"**分析时间**: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"**迭代次数**: {self.iteration_count}",
            f"",
            f"---",
            f"",
            f"## 综合结论",
            f"",
            self.consensus,
            f"",
            f"---",
            f"",
            f"## 专家分析",
            f"",
        ]
        
        for analysis in self.expert_analyses:
            lines.extend([
                f"### {analysis.expert_emoji} {analysis.expert_name}",
                f"",
                analysis.analysis,
                f"",
            ])
        
        lines.extend([
            f"---",
            f"",
            f"## 参考资料",
            f"",
        ])
        
        for i, result in enumerate(self.search_results[:5], 1):
            lines.append(f"{i}. [{result.title}]({result.url})")
        
        return "\n".join(lines)


class AnalysisChain:
    """Main analysis chain that orchestrates the multi-expert analysis"""
    
    def __init__(
        self,
        expert_loader: Optional[ExpertLoader] = None,
        llm_manager: Optional[LLMManager] = None,
        plugin_manager: Optional[PluginManager] = None,
        max_iterations: int = 3,
    ):
        self.expert_loader = expert_loader or ExpertLoader()
        self.llm_manager = llm_manager or get_llm_manager()
        self.plugin_manager = plugin_manager or get_plugin_manager()
        self.max_iterations = max_iterations
    
    async def search(self, query: str, important: bool = False) -> list[SearchResult]:
        """Search for information"""
        try:
            engine = "tavily" if important else None
            results = await self.plugin_manager.search(query, engine=engine)
            return [
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("url", ""),
                    snippet=r.get("snippet", ""),
                    content=r.get("content"),
                )
                for r in results
            ]
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    async def analyze_with_expert(
        self,
        expert: Expert,
        question: str,
        context: str,
    ) -> ExpertAnalysis:
        """Get analysis from a single expert"""
        analysis = await self.llm_manager.analyze_with_expert(
            question=question,
            expert_prompt=expert.system_prompt,
            context=context,
        )
        
        return ExpertAnalysis(
            expert_name=expert.name,
            expert_emoji=expert.metadata.emoji,
            analysis=analysis,
        )
    
    async def generate_consensus(
        self,
        question: str,
        analyses: list[ExpertAnalysis],
    ) -> str:
        """Generate a consensus from multiple expert analyses"""
        analyses_text = "\n\n".join([
            f"### {a.expert_emoji} {a.expert_name} 的分析:\n{a.analysis}"
            for a in analyses
        ])
        
        consensus_prompt = f"""你是一位资深的分析总结专家。请综合以下多位专家的分析，给出最终的综合结论。

## 原始问题
{question}

## 各专家分析
{analyses_text}

## 综合要求
1. 找出各专家观点的共识点
2. 指出存在分歧的地方并给出判断
3. 综合形成最终结论和建议
4. 给出风险提示

请给出你的综合结论："""
        
        return await self.llm_manager.generate(consensus_prompt)
    
    async def run(
        self,
        question: str,
        expert_names: Optional[list[str]] = None,
        callback: Optional[callable] = None,
    ) -> AnalysisResult:
        """
        Run the full analysis chain.
        
        Args:
            question: The question to analyze
            expert_names: Optional list of specific experts to use
            callback: Optional callback for progress updates
        
        Returns:
            Complete analysis result
        """
        def log(msg: str):
            if callback:
                callback(msg)
            print(msg)
        
        # 1. Load experts
        log("📚 加载专家...")
        if expert_names:
            experts = [
                self.expert_loader.get_expert(name)
                for name in expert_names
                if self.expert_loader.get_expert(name)
            ]
        else:
            experts = self.expert_loader.find_relevant_experts(question)
        
        if not experts:
            raise ValueError("没有找到可用的专家")
        
        log(f"✅ 已加载 {len(experts)} 位专家: {', '.join(e.get_display_name() for e in experts)}")
        
        # 2. Get real-time stock data if available
        stock_context = ""
        if HAS_STOCK_PLUGIN:
            log("📈 获取实时股票数据...")
            try:
                stock_context = await get_stock_context(question)
                if stock_context:
                    log("✅ 已获取实时行情数据")
                else:
                    log("ℹ️ 未识别到股票代码")
            except Exception as e:
                log(f"⚠️ 获取股票数据失败: {e}")
        
        # 3. Web search
        log("🔍 搜索相关信息...")
        search_results = await self.search(question)
        search_context = "\n\n".join([
            f"**{r.title}**\n{r.snippet}"
            for r in search_results[:5]
        ])
        log(f"✅ 找到 {len(search_results)} 条相关信息")
        
        # Combine all context
        context = ""
        if stock_context:
            context += f"## 📊 实时行情数据\n\n{stock_context}\n\n"
        if search_context:
            context += f"## 🔍 搜索结果\n\n{search_context}"
        if not context:
            context = "暂无额外背景信息"
        
        # 3. Multi-expert analysis with iterations
        all_analyses: list[ExpertAnalysis] = []
        
        for iteration in range(self.max_iterations):
            log(f"\n🔄 第 {iteration + 1}/{self.max_iterations} 轮分析...")
            
            # Run expert analyses in parallel
            tasks = [
                self.analyze_with_expert(expert, question, context)
                for expert in experts
            ]
            analyses = await asyncio.gather(*tasks)
            all_analyses = list(analyses)
            
            for analysis in all_analyses:
                log(f"  {analysis.expert_emoji} {analysis.expert_name} 完成分析")
            
            # Check if we need more iterations (simplified logic)
            if iteration < self.max_iterations - 1:
                # Search for additional information based on analyses
                log("🔍 补充搜索...")
                supplement_query = f"{question} 详细分析 最新数据"
                new_results = await self.search(supplement_query, important=True)
                if new_results:
                    search_results.extend(new_results[:3])
                    context += "\n\n" + "\n\n".join([
                        f"**{r.title}**\n{r.snippet}"
                        for r in new_results[:3]
                    ])
        
        # 4. Generate consensus
        log("\n📝 生成综合结论...")
        consensus = await self.generate_consensus(question, all_analyses)
        
        log("✅ 分析完成!")
        
        return AnalysisResult(
            question=question,
            search_results=search_results,
            expert_analyses=all_analyses,
            consensus=consensus,
            iteration_count=self.max_iterations,
        )
