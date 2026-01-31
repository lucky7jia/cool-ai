"""LLM integration for Expert Analyst - Ollama support"""

from typing import AsyncIterator, Optional

from langchain_ollama import ChatOllama
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser

from .config import get_config, OllamaConfig


class LLMManager:
    """Manages LLM interactions with Ollama"""
    
    def __init__(self, config: Optional[OllamaConfig] = None):
        if config is None:
            config = get_config().ollama
        self.config = config
        self._llm: Optional[ChatOllama] = None
    
    def get_llm(self) -> ChatOllama:
        """Get or create the LLM instance"""
        if self._llm is None:
            self._llm = ChatOllama(
                base_url=self.config.base_url,
                model=self.config.model,
                temperature=self.config.temperature,
            )
        return self._llm
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Generate a response from the LLM"""
        llm = self.get_llm()
        
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))
        
        response = await llm.ainvoke(messages)
        return response.content
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Generate a streaming response from the LLM"""
        llm = self.get_llm()
        
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))
        
        async for chunk in llm.astream(messages):
            if chunk.content:
                yield chunk.content
    
    async def analyze_with_expert(
        self,
        question: str,
        expert_prompt: str,
        context: str = "",
    ) -> str:
        """Analyze a question using an expert's system prompt"""
        # 开启思考模式
        thinking_instruction = """
<thinking>
请先进行深度思考：
1. 分析提供的数据有哪些关键信息？
2. 这些数据说明了什么趋势？
3. 结合专业知识，应该如何解读？
4. 用户真正关心的是什么？
</thinking>

"""
        
        full_prompt = f"""{thinking_instruction}# 分析任务

## ⚠️ 重要：必须基于以下真实数据进行分析

{context if context else "暂无背景数据"}

---

## 用户问题
{question}

---

## 分析要求（严格遵守）

1. **必须引用上面提供的真实数据**（股价、涨跌幅、PE、成交量等）
2. **禁止编造数据**，只使用上面提供的信息
3. 基于真实数据给出**具体的、可操作的建议**
4. 明确指出**买入/卖出/持有**的建议和理由
5. 给出**具体的价格区间**（基于上面的真实股价数据）

请基于上述真实数据，开始你的专业分析："""
        
        return await self.generate(full_prompt, system_prompt=expert_prompt)


# Global LLM manager instance
_llm_manager: Optional[LLMManager] = None


def get_llm_manager() -> LLMManager:
    """Get global LLM manager instance"""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager()
    return _llm_manager


def set_llm_manager(manager: LLMManager) -> None:
    """Set global LLM manager instance"""
    global _llm_manager
    _llm_manager = manager
