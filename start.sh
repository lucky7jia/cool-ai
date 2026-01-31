#!/bin/bash
# Expert Analyst 启动脚本

cd "$(dirname "$0")"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Expert Analyst 启动中...${NC}"

# 停止旧进程
echo -e "${YELLOW}⏹️  停止旧服务...${NC}"
pkill -9 -f "python.*app.py" 2>/dev/null
pkill -9 -f "gradio" 2>/dev/null
fuser -k 7860/tcp 2>/dev/null
sleep 2

# 确保端口释放
for i in {1..5}; do
    if ! lsof -i :7860 > /dev/null 2>&1; then
        break
    fi
    fuser -k 7860/tcp 2>/dev/null
    sleep 1
done

# 激活虚拟环境
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo -e "${GREEN}✅ 虚拟环境已激活${NC}"
else
    echo -e "${RED}❌ 虚拟环境不存在，请先运行: python3 -m venv .venv${NC}"
    exit 1
fi

# 检查 Ollama
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${RED}❌ Ollama 未运行，请先启动 Ollama${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Ollama 已连接${NC}"

# 启动服务
echo -e "${YELLOW}🌐 启动 Web 服务...${NC}"
nohup python3 src/ui/app.py > /tmp/analyst.log 2>&1 &
PID=$!

# 等待启动
for i in {1..15}; do
    if curl -s http://localhost:7860 > /dev/null 2>&1; then
        echo ""
        echo -e "${GREEN}════════════════════════════════════════${NC}"
        echo -e "${GREEN}✅ 服务启动成功！${NC}"
        echo -e "${GREEN}🌐 访问地址: http://localhost:7860${NC}"
        echo -e "${GREEN}📋 日志文件: /tmp/analyst.log${NC}"
        echo -e "${GREEN}════════════════════════════════════════${NC}"
        exit 0
    fi
    echo -n "."
    sleep 1
done

echo ""
echo -e "${RED}❌ 启动失败，查看日志:${NC}"
tail -20 /tmp/analyst.log
exit 1
