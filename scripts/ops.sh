#!/bin/bash
# ============================================================
# 股票策略研发平台 — 一键运维脚本
# 用法: bash scripts/ops.sh <command>
# ============================================================

set -e

# --- 配置 ---
REMOTE_HOST="root@47.97.26.218"
SSH_KEY="/root/ecs.pem"
SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no -o ConnectTimeout=10"
REMOTE_DIR="/root/stock-platform"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND_URL="https://rogeroger-yu.github.io/stock-platform/"
BACKEND_URL="http://47.97.26.218:80"

# 颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[✗]${NC} $*"; }
ssh_cmd() { ssh $SSH_OPTS "$REMOTE_HOST" "$*"; }

# ============================================================
# 后端相关
# ============================================================

backend_deploy() {
    info "部署后端到远程服务器..."
    rsync -avz --exclude='.venv' --exclude='__pycache__' --exclude='data/parquet' \
        --exclude='*.db' --exclude='test_*.db' --exclude='.pytest_cache' \
        -e "ssh $SSH_OPTS" \
        "$LOCAL_DIR/backend/" "$REMOTE_HOST:$REMOTE_DIR/backend/"
    info "后端文件同步完成"
}

backend_restart() {
    info "重启后端服务..."
    ssh_cmd "pkill -f 'uvicorn app.main' 2>/dev/null || true; sleep 2"
    ssh_cmd "cd $REMOTE_DIR/backend && source .venv/bin/activate && nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 80 > /tmp/uvicorn.log 2>&1 &"
    sleep 3
    ssh_cmd "curl -s http://localhost:80/health" && info "后端重启成功" || error "后端启动失败"
}

backend_status() {
    info "后端状态:"
    ssh_cmd "curl -s http://localhost:80/health 2>/dev/null && echo ''" || warn "后端不可达"
    ssh_cmd "ss -tlnp | grep ':80 ' | head -3"
    ssh_cmd "tail -3 /tmp/uvicorn.log 2>/dev/null"
}

backend_logs() {
    ssh_cmd "tail -${1:-50} /tmp/uvicorn.log"
}

backend_test() {
    info "运行后端测试..."
    ssh_cmd "cd $REMOTE_DIR/backend && source .venv/bin/activate && python -m pytest tests/ -v --tb=short"
}

# ============================================================
# 前端相关
# ============================================================

frontend_build() {
    info "构建前端..."
    cd "$LOCAL_DIR/frontend"
    NODE_OPTIONS="--max-old-space-size=512" npx vite build
    info "前端构建完成: dist/"
}

frontend_deploy() {
    info "部署前端到 GitHub Pages..."
    cd "$LOCAL_DIR/frontend"
    NODE_OPTIONS="--max-old-space-size=512" npx vite build
    cd "$LOCAL_DIR"
    git add -f frontend/dist/
    git commit -m "build: frontend dist $(date +%Y%m%d-%H%M)" || true
    git push origin master
    info "前端已推送，GitHub Actions 将自动部署"
}

frontend_check() {
    info "检查前端部署状态..."
    curl -sL "$FRONTEND_URL" -o /dev/null -w "HTTP %{http_code}\n" 2>&1
    local js_file=$(curl -sL "$FRONTEND_URL" 2>/dev/null | grep -o 'index-[^"]*\.js' | head -1)
    if [ -n "$js_file" ]; then
        local has_api=$(curl -sL "${FRONTEND_URL}assets/$js_file" 2>/dev/null | grep -c '47.97.26.218' || echo 0)
        if [ "$has_api" -gt 0 ]; then
            info "前端已包含正确 API 地址"
        else
            warn "前端 JS 中未找到 API 地址，可能需要重新构建"
        fi
    fi
}

# ============================================================
# 数据相关
# ============================================================

data_download() {
    info "下载股票数据（Sina 数据源）..."
    rsync -avz -e "ssh $SSH_OPTS" \
        "$LOCAL_DIR/backend/download_sina.py" "$REMOTE_HOST:$REMOTE_DIR/backend/" 2>/dev/null || true
    ssh_cmd "cd $REMOTE_DIR/backend && source .venv/bin/activate && python download_sina.py"
}

data_status() {
    info "数据状态:"
    ssh_cmd "ls $REMOTE_DIR/backend/data/parquet/ | wc -l && echo '只股票'"
    ssh_cmd "du -sh $REMOTE_DIR/backend/data/parquet/"
}

data_list() {
    ssh_cmd "ls -la $REMOTE_DIR/backend/data/parquet/"
}

# ============================================================
# 策略相关
# ============================================================

strategy_list() {
    info "策略列表:"
    ssh_cmd "curl -s http://localhost:80/api/strategies | python3 -c \"
import sys, json
data = json.load(sys.stdin)
for s in data:
    print(f\\\"  {s['id']:3d} | {s['strategy_type']:25s} | {s['name']}\\\")
print(f'\\n共 {len(data)} 个策略')
\""
}

strategy_seed() {
    info "初始化默认策略..."
    ssh_cmd "curl -s -X POST http://localhost:80/api/strategies/seed-defaults | python3 -c 'import sys,json; d=json.load(sys.stdin); print(f\"创建 {len(d[\"created\"])} 个策略\")'"
}

strategy_types() {
    info "策略类型:"
    ssh_cmd "curl -s http://localhost:80/api/strategy-types | python3 -c \"
import sys, json
data = json.load(sys.stdin)
for t in data:
    print(f\\\"  {t['type']:25s} | {t['name']} ({t['category']})\\\")
\""
}

# ============================================================
# 回测相关
# ============================================================

backtest_single() {
    local strategy_id=${1:-1}
    local symbols=${2:-"000001"}
    local start=${3:-"2020-01-01"}
    local end=${4:-"2025-01-01"}
    info "单策略回测: strategy=$strategy_id symbols=$symbols"
    ssh_cmd "curl -s -X POST http://localhost:80/api/backtests/run \
        -H 'Content-Type: application/json' \
        -d '{\"strategy_id\": $strategy_id, \"symbols\": [\"$symbols\"], \"start_date\": \"$start\", \"end_date\": \"$end\"}' \
        | python3 -c 'import sys,json; d=json.load(sys.stdin); print(f\"年化: {d[\"annualized_return\"]*100:.2f}%  夏普: {d[\"sharpe_ratio\"]:.3f}  回撤: {d[\"max_drawdown\"]*100:.1f}%\")'"
}

backtest_batch() {
    local symbols=${1:-"000001,600519,002594"}
    local start=${2:-"2020-01-01"}
    local end=${3:-"2024-12-31"}
    local top_n=${4:-10}
    info "批量回测: symbols=$symbols top=$top_n"
    local sym_array=$(echo "$symbols" | sed 's/,/","/g')
    ssh_cmd "curl -s -X POST http://localhost:80/api/backtests/batch \
        -H 'Content-Type: application/json' \
        -d '{\"symbols\": [\"$sym_array\"], \"start_date\": \"$start\", \"end_date\": \"$end\", \"top_n\": $top_n}' \
        | python3 -c \"
import sys, json
d = json.load(sys.stdin)
print(f'回测完成: {d[\"total_strategies\"]} 策略 × {len(d[\"symbols\"])} 标的')
print()
for i, r in enumerate(d['rankings'], 1):
    print(f'  #{i:2d} {r[\"strategy_name\"]:25s} score={r[\"composite_score\"]:.4f} ret={r[\"metrics\"][\"annualized_return\"]*100:.1f}%')
\""
}

# ============================================================
# 环境相关
# ============================================================

env_setup() {
    info "设置本地开发环境..."
    cd "$LOCAL_DIR"

    # 后端
    info "安装后端依赖..."
    cd backend
    python3 -m venv .venv 2>/dev/null || true
    source .venv/bin/activate
    pip install -r requirements.txt -q
    cd ..

    # 前端
    info "安装前端依赖..."
    cd frontend
    npm install
    cd ..

    info "环境设置完成"
}

env_check() {
    info "环境检查:"
    echo ""
    echo "=== 本地 ==="
    echo "Python: $(python3 --version 2>&1)"
    echo "Node:   $(node --version 2>&1)"
    echo "Git:    $(git --version 2>&1)"
    echo ""
    echo "=== 远程 ==="
    ssh_cmd "python3 --version && node --version 2>/dev/null || echo 'node: N/A'"
    echo ""
    echo "=== 后端 ==="
    ssh_cmd "curl -s http://localhost:80/health 2>/dev/null || echo '后端不可达'"
    echo ""
    echo "=== 数据 ==="
    ssh_cmd "ls $REMOTE_DIR/backend/data/parquet/ 2>/dev/null | wc -l && echo '只股票'"
}

# ============================================================
# 模拟交易
# ============================================================

paper_status() {
    info "模拟交易状态:"
    ssh_cmd "curl -s http://localhost:80/api/paper/account | python3 -c 'import sys,json; d=json.load(sys.stdin); print(f\"资金: {d[\"cash\"]:,.0f}  持仓: {len(d[\"positions\"])} 只  总值: {d[\"total_value\"]:,.0f}\")'"
}

paper_daily() {
    info "每日检查..."
    ssh_cmd "curl -s -X POST http://localhost:80/api/paper/daily-check | python3 -c 'import sys,json; d=json.load(sys.stdin); print(f\"日期: {d[\"date\"]}  信号: {len(d[\"signals\"])}  执行: {len(d[\"executed\"])}\")'"
}

# ============================================================
# Git 相关
# ============================================================

git_status() {
    cd "$LOCAL_DIR"
    info "Git 状态:"
    git status -s
    echo ""
    git log --oneline -5
}

git_push() {
    cd "$LOCAL_DIR"
    git add -A
    git commit -m "${1:-update: $(date +%Y-%m-%d)}" || true
    git push origin master
    info "已推送到 GitHub"
}

# ============================================================
# 完整流程
# ============================================================

full_deploy() {
    info "=== 完整部署流程 ==="
    backend_deploy
    backend_restart
    frontend_deploy
    info "=== 部署完成 ==="
    echo ""
    echo "后端: $BACKEND_URL"
    echo "前端: $FRONTEND_URL"
}

daily_ops() {
    info "=== 每日运维 ==="
    backend_status
    echo ""
    data_status
    echo ""
    strategy_list
    echo ""
    paper_status
    paper_daily
    info "=== 每日运维完成 ==="
}

# ============================================================
# 帮助
# ============================================================

help() {
    cat << 'EOF'
股票策略研发平台 — 运维脚本

用法: bash scripts/ops.sh <command> [args...]

后端:
  backend:deploy       部署后端到远程服务器
  backend:restart      重启后端服务
  backend:status       查看后端状态
  backend:logs [N]     查看后端日志 (默认 50 行)
  backend:test         运行后端测试

前端:
  frontend:build       本地构建前端
  frontend:deploy      构建并部署前端到 GitHub Pages
  frontend:check       检查前端部署状态

数据:
  data:download        下载 Top50 股票数据
  data:status          查看数据状态
  data:list            列出数据文件

策略:
  strategy:list        列出所有策略
  strategy:seed        初始化默认策略
  strategy:types       列出策略类型

回测:
  backtest:single [id] [symbol] [start] [end]  单策略回测
  backtest:batch [symbols] [start] [end] [top]  批量回测

模拟交易:
  paper:status         模拟交易状态
  paper:daily          每日检查

环境:
  env:setup            设置本地开发环境
  env:check            检查环境状态

Git:
  git:status           查看 Git 状态
  git:push [message]   提交并推送

完整流程:
  full:deploy          完整部署（后端+前端）
  daily:ops            每日运维检查

示例:
  bash scripts/ops.sh backend:deploy
  bash scripts/ops.sh backtest:batch "000001,600519,002594" 2020-01-01 2024-12-31 10
  bash scripts/ops.sh full:deploy
EOF
}

# ============================================================
# 命令分发
# ============================================================

case "${1:-help}" in
    backend:deploy)     backend_deploy ;;
    backend:restart)    backend_restart ;;
    backend:status)     backend_status ;;
    backend:logs)       backend_logs "${2:-50}" ;;
    backend:test)       backend_test ;;

    frontend:build)     frontend_build ;;
    frontend:deploy)    frontend_deploy ;;
    frontend:check)     frontend_check ;;

    data:download)      data_download ;;
    data:status)        data_status ;;
    data:list)          data_list ;;

    strategy:list)      strategy_list ;;
    strategy:seed)      strategy_seed ;;
    strategy:types)     strategy_types ;;

    backtest:single)    backtest_single "${2:-1}" "${3:-000001}" "${4:-2020-01-01}" "${5:-2025-01-01}" ;;
    backtest:batch)     backtest_batch "${2:-000001,600519,002594}" "${3:-2020-01-01}" "${4:-2024-12-31}" "${5:-10}" ;;

    paper:status)       paper_status ;;
    paper:daily)        paper_daily ;;

    env:setup)          env_setup ;;
    env:check)          env_check ;;

    git:status)         git_status ;;
    git:push)           git_push "${2:-update}" ;;

    full:deploy)        full_deploy ;;
    daily:ops)          daily_ops ;;

    help|*)             help ;;
esac
