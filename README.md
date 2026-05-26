# 股票策略研发平台

量化交易策略的构建、回测、对比分析和模拟交易平台。

## 技术栈

- **后端**: FastAPI + Pandas + akshare + SQLAlchemy
- **前端**: React 18 + TypeScript + Vite + Ant Design + Recharts
- **数据库**: SQLite（策略/回测持久化）+ Parquet（行情数据）
- **部署**: Docker Compose

## 快速开始

```bash
# 启动后端
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload

# 启动前端
cd frontend && npm install && npm run dev

# 下载样本数据
cd backend && python -m app.data.downloader --sample

# 初始化策略库
curl -X POST http://localhost:8000/api/strategies/seed-defaults
```

## 运行测试

```bash
cd backend && python -m pytest tests/ -v
```

## 功能特性

### 策略管理
- 15 个内置策略（6 大族：动量、均值回归、多因子、MACD、KDJ、海龟）
- 支持创建、修改、删除策略
- 策略参数完全可配置

### 回测引擎
- 单股/多股组合回测
- 批量回测 + Top10 排名（综合收益、夏普比、回撤）
- Walk-Forward 优化（IS/OOS 分割）

### 模拟交易
- 纯本地模拟，不连接真实券商
- 策略信号自动转换为订单建议
- 支持回测 vs 模拟交易对比

## API 文档

启动后端后访问: http://localhost:8000/docs

## 项目结构

```
stock-platform/
├── backend/
│   ├── app/
│   │   ├── api/           # API 路由
│   │   ├── core/          # 回测引擎、指标计算
│   │   ├── strategies/    # 策略实现（15 个）
│   │   ├── paper_trade/   # 模拟交易 + 桥接层
│   │   ├── data/          # 数据获取和存储
│   │   └── models/        # 数据库模型
│   └── tests/             # 测试（151 个）
├── frontend/              # React 前端
├── docs/                  # 文档和计划
└── docker-compose.yml
```
