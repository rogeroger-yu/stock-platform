# 股票策略研发平台 — 运维手册

## 快速开始

```bash
# 进入项目目录
cd /root/.openclaw/workspace/stock-platform

# 查看所有命令
bash scripts/ops.sh help

# 完整部署
bash scripts/ops.sh full:deploy

# 每日运维
bash scripts/ops.sh daily:ops
```

## 命令速查

### 后端

| 命令 | 说明 |
|------|------|
| `backend:deploy` | 部署后端到远程服务器（rsync） |
| `backend:restart` | 重启后端服务 |
| `backend:status` | 查看后端状态（健康检查+进程+日志） |
| `backend:logs [N]` | 查看后端日志（默认 50 行） |
| `backend:test` | 运行后端测试（151+ 测试用例） |

### 前端

| 命令 | 说明 |
|------|------|
| `frontend:build` | 本地构建前端（输出到 dist/） |
| `frontend:deploy` | 构建并推送到 GitHub Pages |
| `frontend:check` | 检查前端部署状态和 API 地址 |

### 数据

| 命令 | 说明 |
|------|------|
| `data:download` | 下载 Top50 股票数据（Sina 数据源） |
| `data:status` | 查看数据状态（文件数+大小） |
| `data:list` | 列出所有数据文件 |

### 策略

| 命令 | 说明 |
|------|------|
| `strategy:list` | 列出所有已注册策略 |
| `strategy:seed` | 初始化默认策略（17 个） |
| `strategy:types` | 列出策略类型目录 |

### 回测

| 命令 | 说明 |
|------|------|
| `backtest:single [id] [symbol] [start] [end]` | 单策略回测 |
| `backtest:batch [symbols] [start] [end] [top]` | 批量回测+排名 |

### 模拟交易

| 命令 | 说明 |
|------|------|
| `paper:status` | 模拟交易账户状态 |
| `paper:daily` | 执行每日检查（信号+执行） |

### 环境

| 命令 | 说明 |
|------|------|
| `env:setup` | 设置本地开发环境（venv + npm） |
| `env:check` | 检查本地+远程环境状态 |

### Git

| 命令 | 说明 |
|------|------|
| `git:status` | 查看 Git 状态 |
| `git:push [message]` | 提交并推送 |

### 完整流程

| 命令 | 说明 |
|------|------|
| `full:deploy` | 完整部署（后端 rsync + 重启 + 前端 push） |
| `daily:ops` | 每日运维检查（状态+数据+策略+模拟交易） |

## 核心工作流

### 1. 策略研究循环（每日）

```bash
# 1. 下载/更新数据
bash scripts/ops.sh data:download

# 2. 批量回测所有策略
bash scripts/ops.sh backtest:batch "000001,600519,000858,002594" 2020-01-01 2024-12-31 17

# 3. 查看前端排名和对比
# -> 访问 https://rogeroger-yu.github.io/stock-platform/

# 4. 每日模拟检查
bash scripts/ops.sh paper:daily
```

### 2. 策略复盘（每周）

1. 在前端「批量排名」页面查看各策略表现
2. 在「策略对比」页面叠加净值曲线
3. 分析：哪些策略在什么市场环境下表现好？
4. 调整参数或构建新的复合策略
5. 跑 walk-forward 验证

### 3. 复合策略迭代

1. 在前端「策略详情」页面编辑策略参数
2. 运行回测验证
3. 与单策略对比
4. 重复直到找到更优组合

## 典型工作流

### 1. 修改策略后部署

```bash
# 编辑策略代码
vim backend/app/strategies/composite.py

# 部署后端
bash scripts/ops.sh backend:deploy
bash scripts/ops.sh backend:restart

# 验证
bash scripts/ops.sh strategy:list
```

### 2. 修改前端后部署

```bash
# 编辑前端代码
vim frontend/src/pages/Home.tsx

# 构建并部署
bash scripts/ops.sh frontend:deploy

# 检查部署
bash scripts/ops.sh frontend:check
```

### 3. 下载更多数据

```bash
# 下载 Top50 股票数据
bash scripts/ops.sh data:download

# 查看数据
bash scripts/ops.sh data:status
```

### 4. 运行回测

```bash
# 单策略回测
bash scripts/ops.sh backtest:single 1 000001 2020-01-01 2025-01-01

# 批量回测（3 标的 × 17 策略）
bash scripts/ops.sh backtest:batch "000001,600519,002594" 2020-01-01 2024-12-31 10
```

### 5. 每日运维

```bash
# 完整每日检查
bash scripts/ops.sh daily:ops

# 单独执行模拟交易检查
bash scripts/ops.sh paper:daily
```

## 环境信息

| 项目 | 本地 | 远程服务器 |
|------|------|-----------|
| Python | 3.11.2 | 3.12.3 |
| Node.js | v22.22.2 | N/A |
| 后端地址 | localhost:8000 | 47.97.26.218:80 |
| 前端地址 | localhost:5173 | GitHub Pages |
| 数据目录 | backend/data/parquet/ | /root/stock-platform/backend/data/parquet/ |

## 配置

脚本配置在 `scripts/ops.sh` 顶部：

```bash
REMOTE_HOST="root@47.97.26.218"    # 远程服务器
SSH_KEY="/root/ecs.pem"            # SSH 密钥
REMOTE_DIR="/root/stock-platform"  # 远程目录
FRONTEND_URL="https://rogeroger-yu.github.io/stock-platform/"
BACKEND_URL="http://47.97.26.218:80"
```

## 故障排查

### 后端不可达

```bash
# 检查进程
bash scripts/ops.sh backend:status

# 查看日志
bash scripts/ops.sh backend:logs 20

# 重启
bash scripts/ops.sh backend:restart
```

### 前端显示旧版本

```bash
# 重新构建并部署
bash scripts/ops.sh frontend:deploy

# 检查 API 地址
bash scripts/ops.sh frontend:check
```

### 数据下载失败

```bash
# 检查网络
ssh -i /root/ecs.pem root@47.97.26.218 'curl -s https://finance.sina.com.cn -o /dev/null -w "%{http_code}"'

# 重试下载
bash scripts/ops.sh data:download
```

### 测试失败

```bash
# 运行测试
bash scripts/ops.sh backend:test

# 清理测试数据库重试
ssh -i /root/ecs.pem root@47.97.26.218 'cd /root/stock-platform/backend && rm -f test_*.db'
bash scripts/ops.sh backend:test
```
