# 股票策略研发平台 — 运维变更日志

## 2026-05-26

### 新增
- 运维脚本 `scripts/ops.sh` — 一键执行所有常见操作
- 运维手册 `scripts/OPS_MANUAL.md` — 命令速查+工作流+故障排查
- 50 只 Top 权重股数据（10 年日线，Sina 数据源）
- `.env.production` — 前端生产环境 API 地址配置

### 修改
- 后端端口从 8000 改为 80（便于外网访问）
- 前端构建流程：使用 `.env.production` 注入 API 地址
- 部署流程：后端 rsync + 前端 GitHub Pages 自动部署

### 运维命令速查

```bash
# 查看所有命令
bash scripts/ops.sh help

# 常用命令
bash scripts/ops.sh backend:deploy      # 部署后端
bash scripts/ops.sh frontend:deploy     # 部署前端
bash scripts/ops.sh data:download       # 下载数据
bash scripts/ops.sh backtest:batch      # 批量回测
bash scripts/ops.sh daily:ops           # 每日运维
bash scripts/ops.sh full:deploy         # 完整部署
```

### 环境配置

| 配置项 | 值 |
|--------|-----|
| 远程服务器 | root@47.97.26.218 |
| SSH 密钥 | /root/ecs.pem |
| 后端地址 | http://47.97.26.218:80 |
| 前端地址 | https://rogeroger-yu.github.io/stock-platform/ |
| 远程目录 | /root/stock-platform |
| 数据源 | Sina Finance (akshare) |
