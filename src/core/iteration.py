"""Iteration and self-verification system"""

import asyncio
import json
from dataclasses import dataclass
from typing import Callable, Optional

from .chain import AnalysisChain, AnalysisResult, ExpertAnalysis
from .config import get_config
from .llm import get_llm_manager


@dataclass
class IterationResult:
    """Result of an iteration cycle"""
    iteration_number: int
    result: AnalysisResult
    gaps_identified: list[str]
    supplemental_queries: list[str]
    consensus_score: float


class IterativeAnalyzer:
    """
    Iterative analysis with self-verification.
    
    The key insight: local models may have limited capability,
    but multiple iterations can compensate by:
    1. Cross-validating expert opinions
    2. Identifying information gaps
    3. Supplementing with additional searches
    4. Refining conclusions
    """

    def __init__(
        self,
        chain: AnalysisChain,
        max_iterations: Optional[int] = None,
        consensus_threshold: float = 0.8,
        on_progress: Optional[Callable[[str], None]] = None,
    ):
        config = get_config()
        self.chain = chain
        self.max_iterations = max_iterations or config.max_iterations
        self.consensus_threshold = consensus_threshold
        self.on_progress = on_progress or (lambda x: None)

    def _report_progress(self, message: str) -> None:
        """Report progress to callback"""
        self.on_progress(message)

    async def _identify_gaps(
        self,
        query: str,
        analyses: list[ExpertAnalysis],
    ) -> tuple[list[str], list[str]]:
        """
        Identify information gaps and generate supplemental queries.
        
        Returns:
            Tuple of (gaps, supplemental_queries)
        """
        llm = get_llm_manager()
        
        # Build a prompt to identify gaps
        analyses_text = "\n\n".join([
            f"**{a.expert_name}**: {a.analysis[:500]}..."
            for a in analyses
        ])

        gap_prompt = """你是一位研究方法专家，负责识别分析中的信息缺口。

请分析各专家的意见，找出：
1. 哪些观点存在分歧？
2. 哪些信息还不够充分？
3. 需要补充搜索什么内容？

请用JSON格式输出：
{
  "gaps": ["缺口1", "缺口2"],
  "queries": ["补充搜索1", "补充搜索2"]
}"""

        gap_query = f"""原始问题：{query}

各专家分析：
{analyses_text}

请识别信息缺口和需要补充的搜索。"""

        result = await llm.generate(gap_query, system_prompt=gap_prompt)

        # Simple parsing
        gaps = []
        queries = []
        
        try:
            # Try to find JSON in the response
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(result[start:end])
                gaps = data.get("gaps", [])
                queries = data.get("queries", [])
        except Exception:
            # If parsing fails, use the raw text as a gap
            gaps = [result[:200]]
            queries = []

        return gaps, queries

    async def _calculate_consensus(
        self,
        analyses: list[ExpertAnalysis],
    ) -> float:
        """
        Calculate consensus score among experts.
        
        Returns a score between 0 and 1.
        """
        if len(analyses) < 2:
            return 1.0

        # Simple heuristic: check for keywords indicating agreement/disagreement
        agreement_keywords = ["同意", "一致", "相似", "支持", "认同", "agree", "similar"]
        disagreement_keywords = ["不同意", "分歧", "反对", "质疑", "disagree", "differ"]

        total_agreement = 0
        total_disagreement = 0

        for analysis in analyses:
            text = analysis.analysis.lower()
            for kw in agreement_keywords:
                total_agreement += text.count(kw)
            for kw in disagreement_keywords:
                total_disagreement += text.count(kw)

        if total_agreement + total_disagreement == 0:
            return 0.7  # Default moderate consensus

        score = total_agreement / (total_agreement + total_disagreement + 1)
        return min(1.0, max(0.0, 0.5 + score * 0.5))

    async def run(
        self,
        query: str,
        experts: Optional[list[str]] = None,
    ) -> AnalysisResult:
        """
        Run iterative analysis with self-verification.
        
        Args:
            query: User's question
            experts: Optional list of expert names
            
        Returns:
            Final analysis result after iterations
        """
        self._report_progress(f"🔄 开始迭代分析 (最多 {self.max_iterations} 轮)...")

        current_query = query
        all_search_results = []
        iteration = 0
        result = None

        while iteration < self.max_iterations:
            iteration += 1
            self._report_progress(f"\n📊 第 {iteration} 轮迭代...")

            # Run analysis chain
            result = await self.chain.run(
                question=current_query,
                expert_names=experts,
                callback=self._report_progress,
            )

            # Accumulate search results
            all_search_results.extend(result.search_results)

            # Calculate consensus
            consensus_score = await self._calculate_consensus(result.expert_analyses)
            self._report_progress(f"  📈 共识度: {consensus_score:.1%}")

            # Check if consensus is reached
            if consensus_score >= self.consensus_threshold:
                self._report_progress(f"✅ 达成共识，结束迭代")
                result.iteration_count = iteration
                result.search_results = list(set(all_search_results))
                return result

            # Identify gaps for next iteration
            if iteration < self.max_iterations:
                self._report_progress("  🔍 识别信息缺口...")
                gaps, supplemental_queries = await self._identify_gaps(
                    query, result.expert_analyses
                )

                if not supplemental_queries:
                    self._report_progress("  ℹ️ 没有新的搜索建议，结束迭代")
                    result.iteration_count = iteration
                    result.search_results = list(set(all_search_results))
                    return result

                # Update query for next iteration
                current_query = f"{query}\n\n补充信息需求：{'; '.join(supplemental_queries[:2])}"
                self._report_progress(f"  📝 补充搜索: {supplemental_queries[:2]}")

        self._report_progress(f"⏹️ 达到最大迭代次数 ({self.max_iterations})")
        if result:
            result.iteration_count = iteration
            result.search_results = list(set(all_search_results))
        return result
