"""Gradio Web UI for Expert Analyst - Beautiful Edition"""

import asyncio
from typing import Optional, Generator
from concurrent.futures import ThreadPoolExecutor
import threading

import gradio as gr

# 全局 event loop（在独立线程中运行）
_loop: Optional[asyncio.AbstractEventLoop] = None
_loop_thread: Optional[threading.Thread] = None


def _start_background_loop(loop: asyncio.AbstractEventLoop):
    """在后台线程中运行 event loop"""
    asyncio.set_event_loop(loop)
    loop.run_forever()


def get_or_create_loop() -> asyncio.AbstractEventLoop:
    """获取或创建全局 event loop"""
    global _loop, _loop_thread
    if _loop is None or not _loop.is_running():
        _loop = asyncio.new_event_loop()
        _loop_thread = threading.Thread(target=_start_background_loop, args=(_loop,), daemon=True)
        _loop_thread.start()
    return _loop


def run_async(coro):
    """在全局 event loop 中运行异步任务"""
    loop = get_or_create_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()

from src.core.chain import AnalysisChain, AnalysisResult
from src.core.expert import ExpertLoader
from src.core.config import get_config, Config
from src.core.plugin import get_plugin_manager, PluginManager
from src.core.llm import LLMManager, set_llm_manager


# Global state
_analysis_result: Optional[AnalysisResult] = None


# Custom CSS for beautiful UI
CUSTOM_CSS = """
/* 主题色 */
:root {
    --primary-color: #6366f1;
    --primary-hover: #4f46e5;
    --success-color: #10b981;
    --warning-color: #f59e0b;
    --danger-color: #ef4444;
    --bg-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* 整体背景 */
.gradio-container {
    background: linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* 标题区域 */
.header-title {
    background: var(--bg-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-size: 2.5rem !important;
    font-weight: 800 !important;
    text-align: center;
    margin-bottom: 0.5rem !important;
}

.header-subtitle {
    text-align: center;
    color: #64748b;
    font-size: 1.1rem;
    margin-bottom: 1.5rem;
}

/* 卡片样式 */
.card {
    background: white;
    border-radius: 16px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    padding: 1.5rem;
    margin-bottom: 1rem;
}

/* 按钮美化 */
.primary-btn {
    background: var(--bg-gradient) !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 14px 28px !important;
    font-size: 1.1rem !important;
    font-weight: 600 !important;
    color: white !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 14px 0 rgba(99, 102, 241, 0.4) !important;
}

.primary-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px 0 rgba(99, 102, 241, 0.5) !important;
}

.primary-btn:disabled {
    opacity: 0.6 !important;
    cursor: not-allowed !important;
    transform: none !important;
}

/* 输入框美化 */
.input-box textarea {
    border-radius: 12px !important;
    border: 2px solid #e2e8f0 !important;
    padding: 16px !important;
    font-size: 1rem !important;
    transition: border-color 0.2s ease !important;
}

.input-box textarea:focus {
    border-color: var(--primary-color) !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1) !important;
}

/* 专家卡片 */
.expert-card {
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
    border-radius: 12px;
    padding: 12px 16px;
    margin: 8px 0;
    border-left: 4px solid var(--primary-color);
}

/* 进度显示 */
.progress-box {
    background: #f1f5f9;
    border-radius: 12px;
    padding: 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    max-height: 200px;
    overflow-y: auto;
}

/* 结果区域 */
.result-box {
    background: white;
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
}

/* 标签页美化 */
.tabs {
    border-radius: 12px !important;
    overflow: hidden;
}

.tab-nav button {
    font-weight: 600 !important;
    padding: 12px 24px !important;
}

.tab-nav button.selected {
    background: var(--primary-color) !important;
    color: white !important;
}

/* 滑块美化 */
input[type="range"] {
    accent-color: var(--primary-color);
}

/* 复选框美化 */
input[type="checkbox"]:checked {
    background-color: var(--primary-color) !important;
    border-color: var(--primary-color) !important;
}

/* 动画 */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.analyzing {
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

/* 响应式 */
@media (max-width: 768px) {
    .header-title {
        font-size: 1.8rem !important;
    }
}
"""


def _register_plugins(plugin_manager: PluginManager, config: Config):
    """Register all plugins"""
    try:
        from plugins.search.duckduckgo.plugin import DuckDuckGoPlugin
        ddg = DuckDuckGoPlugin()
        loop = asyncio.new_event_loop()
        loop.run_until_complete(ddg.initialize({}))
        loop.close()
        plugin_manager.register(ddg)
        print("✅ 搜索插件已加载")
    except Exception as e:
        print(f"⚠️ 搜索插件加载失败: {e}")

    try:
        from plugins.export.wechat.plugin import WeChatExportPlugin
        from plugins.export.xiaohongshu.plugin import XiaohongshuExportPlugin
        from plugins.export.news.plugin import NewsExportPlugin
        
        for plugin_cls in [WeChatExportPlugin, XiaohongshuExportPlugin, NewsExportPlugin]:
            plugin = plugin_cls()
            loop = asyncio.new_event_loop()
            loop.run_until_complete(plugin.initialize({}))
            loop.close()
            plugin_manager.register(plugin)
        print("✅ 导出插件已加载")
    except Exception as e:
        print(f"⚠️ 导出插件加载失败: {e}")


def create_app() -> gr.Blocks:
    """Create the Gradio application"""
    global _analysis_result
    
    print("🚀 初始化 Expert Analyst...")
    
    config = get_config()
    print(f"📡 Ollama: {config.ollama.base_url}, 模型: {config.ollama.model}")
    
    llm = LLMManager(config.ollama)
    set_llm_manager(llm)
    print("✅ LLM 已连接")
    
    expert_loader = ExpertLoader(config.experts_dir)
    experts = expert_loader.load_all()
    print(f"✅ 已加载 {len(experts)} 位专家")
    
    plugin_manager = get_plugin_manager()
    _register_plugins(plugin_manager, config)
    
    expert_choices = [(f"{e.metadata.emoji} {e.name}", e.name) for e in experts]
    
    def run_analysis_with_progress(
        question: str, 
        selected_experts: list, 
        iterations: int,
    ) -> Generator:
        """Run the analysis with progress updates"""
        global _analysis_result
        
        if not question or not question.strip():
            yield "❌ 请输入要分析的问题", "", "请先输入问题", gr.update(interactive=True)
            return
        
        print(f"\n{'='*50}")
        print(f"📝 新分析请求: {question}")
        print(f"{'='*50}\n")
        
        progress_lines = []
        
        def add_progress(msg: str):
            progress_lines.append(f"• {msg}")
            print(msg)
        
        def get_progress_html():
            return "\n".join(progress_lines[-8:]) if progress_lines else "准备中..."
        
        try:
            chain = AnalysisChain(
                expert_loader=expert_loader,
                plugin_manager=plugin_manager,
                max_iterations=iterations,
            )
            
            add_progress("🚀 初始化分析引擎")
            yield "⏳ 初始化中...", "", get_progress_html(), gr.update(interactive=False)
            
            # 使用全局 event loop 运行异步代码
            result = run_async(_run_analysis_async(
                chain, question, selected_experts, add_progress
            ))
            
            _analysis_result = result
            
            # Format output with better styling
            consensus = f"""## 🎯 综合结论

{result.consensus}

---
*基于 {len(result.expert_analyses)} 位专家分析，迭代 {result.iteration_count} 次*
"""
            
            full_report = result.to_markdown()
            if hasattr(result, 'stock_data') and result.stock_data:
                full_report = f"## 📊 实时行情数据\n\n{result.stock_data}\n\n---\n\n" + full_report
            
            add_progress("✅ 分析完成！")
            yield consensus, full_report, get_progress_html(), gr.update(interactive=True)
            
        except Exception as e:
            error_msg = f"❌ 分析失败: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            add_progress(error_msg)
            yield error_msg, "", get_progress_html(), gr.update(interactive=True)
    
    def export_content(format_name: str):
        global _analysis_result
        if _analysis_result is None:
            return "请先进行分析"
        try:
            return run_async(plugin_manager.export(
                _analysis_result.to_markdown(),
                format_name,
                {"title": _analysis_result.question, "question": _analysis_result.question},
            ))
        except Exception as e:
            return f"导出失败: {str(e)}"
    
    # Build beautiful UI
    print("🎨 构建界面...")
    
    with gr.Blocks(title="Expert Analyst - AI专家分析助手") as app:
        
        # Header
        gr.HTML("""
        <div style="text-align: center; padding: 2rem 0 1rem;">
            <h1 style="background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%); 
                       -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                       font-size: 2.5rem; font-weight: 800; margin: 0;">
                🎯 Expert Analyst
            </h1>
            <p style="color: #64748b; font-size: 1.1rem; margin-top: 0.5rem;">
                AI多专家协作分析 · 解决信息不对称 · 迭代自证机制
            </p>
        </div>
        """)
        
        with gr.Row():
            # Left Column - Input
            with gr.Column(scale=2):
                with gr.Group():
                    question_input = gr.Textbox(
                        label="💭 输入你的问题",
                        placeholder="例如：SpaceX 星舰发射对航天股有何影响？Tesla 未来走势如何？",
                        lines=4,
                        elem_classes=["input-box"],
                    )
                
                with gr.Row():
                    with gr.Column(scale=2):
                        expert_select = gr.CheckboxGroup(
                            choices=expert_choices,
                            label="👥 选择专家（留空自动匹配）",
                            value=[],
                        )
                    with gr.Column(scale=1):
                        iteration_slider = gr.Slider(
                            minimum=1,
                            maximum=5,
                            value=2,
                            step=1,
                            label="🔄 迭代次数",
                        )
                
                analyze_btn = gr.Button(
                    "🔍 开始分析",
                    variant="primary",
                    size="lg",
                    elem_classes=["primary-btn"],
                )
                
                with gr.Accordion("📊 分析进度", open=True):
                    progress_display = gr.Markdown(
                        value="*等待开始分析...*",
                        elem_classes=["progress-box"],
                    )
            
            # Right Column - Experts
            with gr.Column(scale=1):
                gr.HTML("""
                <div style="background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
                            border-radius: 16px; padding: 20px; border-left: 4px solid #6366f1;">
                    <h3 style="margin: 0 0 16px; color: #1e293b; font-size: 1.2rem;">
                        🧠 可用专家
                    </h3>
                </div>
                """)
                for expert in experts:
                    gr.HTML(f"""
                    <div style="background: white; border-radius: 12px; padding: 14px 16px; 
                                margin: 8px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                                border-left: 3px solid {'#6366f1' if expert.name == 'finance' else '#10b981' if expert.name == 'policy' else '#f59e0b' if expert.name == 'industry' else '#ef4444'};">
                        <div style="font-weight: 600; color: #1e293b; margin-bottom: 4px;">
                            {expert.metadata.emoji} {expert.name}
                        </div>
                        <div style="color: #64748b; font-size: 0.85rem;">
                            {expert.description[:40]}...
                        </div>
                    </div>
                    """)
        
        gr.HTML("<div style='height: 24px;'></div>")
        
        # Results Section
        with gr.Tabs() as tabs:
            with gr.TabItem("📊 分析结果", id=0):
                consensus_output = gr.Markdown(
                    value="*等待分析...*",
                    elem_classes=["result-box"],
                )
            
            with gr.TabItem("📝 完整报告", id=1):
                full_report = gr.Markdown(elem_classes=["result-box"])
            
            with gr.TabItem("📤 导出", id=2):
                with gr.Row():
                    export_format = gr.Radio(
                        choices=[
                            ("📱 公众号", "wechat"),
                            ("📕 小红书", "xiaohongshu"),
                            ("📰 新闻稿", "news"),
                        ],
                        value="wechat",
                        label="选择导出格式",
                    )
                    export_btn = gr.Button("📥 导出内容", variant="secondary")
                
                export_output = gr.Textbox(
                    label="导出内容（选中后 Ctrl+C 复制）",
                    lines=15,
                )
        
        # Footer
        gr.HTML("""
        <div style="text-align: center; padding: 2rem 0 1rem; color: #94a3b8; font-size: 0.9rem;">
            <p>Powered by Ollama + LangChain · Made with ❤️</p>
        </div>
        """)
        
        # Event handlers
        analyze_btn.click(
            fn=run_analysis_with_progress,
            inputs=[question_input, expert_select, iteration_slider],
            outputs=[consensus_output, full_report, progress_display, analyze_btn],
        )
        
        export_btn.click(
            fn=export_content,
            inputs=[export_format],
            outputs=[export_output],
        )
    
    print("✅ 界面构建完成")
    return app


async def _run_analysis_async(chain, question, selected_experts, callback):
    """Async analysis wrapper"""
    from plugins.data.stock import get_stock_context
    
    callback("📚 加载专家团队...")
    
    if selected_experts:
        experts = [chain.expert_loader.get_expert(name) for name in selected_experts if chain.expert_loader.get_expert(name)]
    else:
        experts = chain.expert_loader.find_relevant_experts(question)
    
    if not experts:
        raise ValueError("没有找到可用的专家")
    
    callback(f"✅ {len(experts)} 位专家就绪")
    
    callback("📈 获取实时行情数据...")
    stock_context = ""
    try:
        stock_context = await get_stock_context(question)
        if stock_context:
            callback("✅ 已获取实时股票数据")
    except Exception as e:
        callback(f"⚠️ 股票数据: {e}")
    
    callback("🔍 搜索最新资讯...")
    search_results = await chain.search(question)
    callback(f"✅ 找到 {len(search_results)} 条相关信息")
    
    search_context = "\n\n".join([
        f"**{r.title}**\n{r.snippet}\n🔗 {r.url}"
        for r in search_results[:5]
    ])
    
    context = ""
    if stock_context:
        context += f"## 📊 实时行情数据\n\n{stock_context}\n\n"
    if search_context:
        context += f"## 🔍 搜索结果\n\n{search_context}"
    
    all_analyses = []
    for iteration in range(chain.max_iterations):
        callback(f"🔄 第 {iteration + 1}/{chain.max_iterations} 轮分析")
        
        for expert in experts:
            callback(f"   💭 {expert.get_display_name()} 思考中...")
            analysis = await chain.analyze_with_expert(expert, question, context)
            all_analyses.append(analysis)
    
    callback("📝 生成综合结论...")
    consensus = await chain.generate_consensus(question, all_analyses[-len(experts):])
    
    from src.core.chain import AnalysisResult
    result = AnalysisResult(
        question=question,
        search_results=search_results,
        expert_analyses=all_analyses[-len(experts):],
        consensus=consensus,
        iteration_count=chain.max_iterations,
    )
    result.stock_data = stock_context
    
    return result


if __name__ == "__main__":
    app = create_app()
    print("🌐 启动服务: http://localhost:7860")
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        css=CUSTOM_CSS,
        theme=gr.themes.Soft(
            primary_hue="indigo",
            secondary_hue="purple",
            neutral_hue="slate",
            font=gr.themes.GoogleFont("Inter"),
        )
    )
