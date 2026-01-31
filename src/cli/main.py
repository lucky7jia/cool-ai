"""CLI entry point for Expert Analyst"""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.markdown import Markdown

app = typer.Typer(
    name="analyst",
    help="AI专家分析助手 - 解决信息不对称问题",
    add_completion=False,
)
console = Console()


@app.command()
def init(
    force: bool = typer.Option(False, "--force", "-f", help="强制重新初始化"),
):
    """初始化 Expert Analyst 配置"""
    from src.core.config import Config
    
    config_dir = Path.home() / ".analyst"
    config_file = config_dir / "config.yaml"
    
    if config_file.exists() and not force:
        console.print("[yellow]配置文件已存在。使用 --force 强制重新初始化。[/yellow]")
        return
    
    console.print(Panel.fit(
        "[bold blue]Expert Analyst 初始化向导[/bold blue]\n\n"
        "欢迎使用 AI 专家分析助手！",
        title="🎯 Expert Analyst",
    ))
    
    # Interactive configuration
    console.print("\n[bold]Ollama 配置[/bold]")
    base_url = typer.prompt("Ollama 地址", default="http://localhost:11434")
    model = typer.prompt("默认模型", default="qwen2.5vl:7b")
    
    console.print("\n[bold]搜索配置[/bold]")
    tavily_key = typer.prompt("Tavily API Key (可选，按回车跳过)", default="", show_default=False)
    
    # Create config
    config = Config()
    config.ollama.base_url = base_url
    config.ollama.model = model
    if tavily_key:
        config.search.tavily_api_key = tavily_key
    
    # Save config
    config.save(config_file)
    
    # Create default experts directory
    experts_dir = Path.cwd() / "experts"
    if not experts_dir.exists():
        experts_dir.mkdir(parents=True)
        console.print(f"[green]✅ 创建专家目录: {experts_dir}[/green]")
    
    console.print(f"\n[green]✅ 配置已保存到: {config_file}[/green]")
    console.print("\n[bold]下一步:[/bold]")
    console.print("  1. 运行 [cyan]analyst experts list[/cyan] 查看可用专家")
    console.print("  2. 运行 [cyan]analyst ask \"你的问题\"[/cyan] 开始分析")


@app.command()
def ask(
    question: str = typer.Argument(..., help="要分析的问题"),
    experts: Optional[str] = typer.Option(None, "--experts", "-e", help="指定专家，逗号分隔"),
    iterations: int = typer.Option(3, "--iterations", "-i", help="迭代次数"),
    export: Optional[str] = typer.Option(None, "--export", help="导出格式，如: wechat,xiaohongshu"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="输出文件路径"),
):
    """分析问题并生成专家报告"""
    from src.core.chain import AnalysisChain
    from src.core.expert import ExpertLoader
    from src.core.config import get_config
    from src.core.plugin import get_plugin_manager
    
    # Initialize
    config = get_config()
    expert_loader = ExpertLoader(config.experts_dir)
    plugin_manager = get_plugin_manager()
    
    # Register default plugins
    _register_default_plugins(plugin_manager, config)
    
    chain = AnalysisChain(
        expert_loader=expert_loader,
        plugin_manager=plugin_manager,
        max_iterations=iterations,
    )
    
    console.print(Panel.fit(
        f"[bold]{question}[/bold]",
        title="🎯 分析问题",
    ))
    
    # Parse expert names
    expert_names = None
    if experts:
        expert_names = [e.strip() for e in experts.split(",")]
    
    # Run analysis
    def progress_callback(msg: str):
        console.print(msg)
    
    try:
        result = asyncio.run(chain.run(
            question=question,
            expert_names=expert_names,
            callback=progress_callback,
        ))
    except Exception as e:
        console.print(f"[red]❌ 分析失败: {e}[/red]")
        raise typer.Exit(1)
    
    # Display result
    console.print("\n")
    console.print(Panel(
        Markdown(result.consensus),
        title="📊 综合结论",
        border_style="green",
    ))
    
    # Show expert analyses
    for analysis in result.expert_analyses:
        console.print(Panel(
            Markdown(analysis.analysis[:500] + "..." if len(analysis.analysis) > 500 else analysis.analysis),
            title=f"{analysis.expert_emoji} {analysis.expert_name}",
            border_style="blue",
        ))
    
    # Export if requested
    if export:
        export_formats = [f.strip() for f in export.split(",")]
        for fmt in export_formats:
            try:
                exported = asyncio.run(plugin_manager.export(
                    result.to_markdown(),
                    fmt,
                    {"title": question, "question": question},
                ))
                
                output_path = output or Path(f"output_{fmt}.md")
                output_path.write_text(exported, encoding="utf-8")
                console.print(f"[green]✅ 已导出: {output_path}[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠️ 导出 {fmt} 失败: {e}[/yellow]")
    
    # Save markdown
    if output:
        output.write_text(result.to_markdown(), encoding="utf-8")
        console.print(f"[green]✅ 报告已保存: {output}[/green]")


@app.command("experts")
def experts_cmd(
    action: str = typer.Argument("list", help="操作: list, add"),
    path: Optional[Path] = typer.Argument(None, help="EXPERT.md 文件路径 (用于 add)"),
):
    """管理专家"""
    from src.core.expert import ExpertLoader
    from src.core.config import get_config
    
    config = get_config()
    loader = ExpertLoader(config.experts_dir)
    
    if action == "list":
        experts = loader.load_all()
        
        if not experts:
            console.print("[yellow]没有找到专家。请在 experts/ 目录下创建 EXPERT.md 文件。[/yellow]")
            return
        
        table = Table(title="可用专家")
        table.add_column("名称", style="cyan")
        table.add_column("描述")
        table.add_column("领域", style="green")
        table.add_column("优先级", justify="center")
        
        for expert in experts:
            table.add_row(
                f"{expert.metadata.emoji} {expert.name}",
                expert.description[:50] + "..." if len(expert.description) > 50 else expert.description,
                ", ".join(expert.metadata.domains),
                str(expert.metadata.priority),
            )
        
        console.print(table)
    
    elif action == "add":
        if not path:
            console.print("[red]请指定 EXPERT.md 文件路径[/red]")
            raise typer.Exit(1)
        
        if not path.exists():
            console.print(f"[red]文件不存在: {path}[/red]")
            raise typer.Exit(1)
        
        # Copy to experts directory
        import shutil
        expert_dir = Path(config.experts_dir) / path.stem
        expert_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(path, expert_dir / "EXPERT.md")
        
        console.print(f"[green]✅ 专家已添加: {expert_dir}[/green]")
    
    else:
        console.print(f"[red]未知操作: {action}[/red]")


@app.command()
def ui():
    """启动 Web UI"""
    console.print("[cyan]启动 Gradio Web UI...[/cyan]")
    try:
        from src.ui.app import create_app
        app = create_app()
        app.launch(share=False)
    except ImportError as e:
        console.print(f"[red]启动 UI 失败: {e}[/red]")
        console.print("[yellow]请确保已安装 gradio: pip install gradio[/yellow]")


def _register_default_plugins(plugin_manager, config):
    """Register default search and export plugins"""
    from plugins.search.duckduckgo.plugin import DuckDuckGoPlugin
    
    # Register DuckDuckGo
    ddg = DuckDuckGoPlugin()
    asyncio.run(ddg.initialize({}))
    plugin_manager.register(ddg)
    
    # Register Tavily if API key is available
    if config.search.tavily_api_key:
        try:
            from plugins.search.tavily.plugin import TavilyPlugin
            tavily = TavilyPlugin()
            asyncio.run(tavily.initialize({"api_key": config.search.tavily_api_key}))
            plugin_manager.register(tavily)
        except ImportError:
            pass
    
    # Register export plugins
    try:
        from plugins.export.wechat.plugin import WeChatExportPlugin
        from plugins.export.xiaohongshu.plugin import XiaohongshuExportPlugin
        from plugins.export.news.plugin import NewsExportPlugin
        
        for plugin_cls in [WeChatExportPlugin, XiaohongshuExportPlugin, NewsExportPlugin]:
            plugin = plugin_cls()
            asyncio.run(plugin.initialize({}))
            plugin_manager.register(plugin)
    except ImportError:
        pass


if __name__ == "__main__":
    app()
