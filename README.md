# 🎯 Expert Analyst

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-000000?style=for-the-badge&logo=ollama&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-Orchestration-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)
![Gradio](https://img.shields.io/badge/Gradio-Web_UI-FF7C00?style=for-the-badge&logo=gradio&logoColor=white)

**AI 多专家协作分析系统 · 解决信息不对称 · 迭代自证机制**

</div>

---

## ✨ 功能特性

| 🧠 多专家协作 | 🔄 迭代自证 | 🔍 智能搜索 | 📤 多平台导出 |
|:---:|:---:|:---:|:---:|
| 金融/政策/行业/风险 | 多轮交叉验证 | 实时行情数据 | 公众号/小红书/新闻稿 |

---

## 🚀 快速开始

```bash
# 克隆 & 安装
git clone https://github.com/yourusername/expert-analyst.git
cd expert-analyst
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# 启动（需先运行 Ollama）
./start.sh
# 访问 http://localhost:7860
```

## 📸 使用示例

```bash
# Web UI
./start.sh

# 命令行
python run.py ask "Tesla 股票是否值得买入"
python run.py ask "问题" --experts finance,policy
```

---

## 📁 项目结构

```
expert-analyst/
├── experts/        # 🧠 专家定义 (finance/policy/industry/risk)
├── plugins/        # 🔌 插件 (search/data/export)
├── src/            # 🔧 核心代码
└── start.sh        # 🚀 启动脚本
```

---

## 🛠️ 技术栈

**LangChain** · **Ollama** · **Gradio** · **Typer** · **httpx**

---

## 📝 License

[MIT](LICENSE)

---

<div align="center">

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=yourusername/expert-analyst&type=Date)](https://star-history.com/#yourusername/expert-analyst&Date)

**Made with ❤️ by Lucky**

</div>
