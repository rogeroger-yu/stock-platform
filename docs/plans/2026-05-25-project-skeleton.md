# Step 0: 项目骨架 — FastAPI + React/Vite + Docker Compose

## 目标
搭建一个 localhost 能跑的全栈项目骨架：
- Python FastAPI 后端 (port 8000)
- React + Vite + TypeScript 前端 (port 5173, dev mode)
- docker-compose 一键启动（可选，先本地跑通）
- SQLite 数据库（回测元数据）
- Parquet 文件存储（行情数据）

## 目录结构

```
stock-platform/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app + CORS
│   │   ├── config.py            # 配置（DB路径、数据目录等）
│   │   ├── models/              # SQLAlchemy/Pydantic models
│   │   │   ├── __init__.py
│   │   │   └── backtest.py      # 回测结果模型
│   │   ├── routers/             # API routes
│   │   │   ├── __init__.py
│   │   │   ├── health.py        # /api/health
│   │   │   └── backtest.py      # /api/backtest/*
│   │   ├── services/            # 业务逻辑
│   │   │   ├── __init__.py
│   │   │   └── backtest_service.py
│   │   └── db.py                # SQLite engine + session
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_health.py
│   │   └── test_backtest_api.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── api/                 # API 调用层
│   │   │   └── client.ts
│   │   ├── pages/
│   │   │   ├── Home.tsx         # 策略列表
│   │   │   └── BacktestDetail.tsx
│   │   └── components/
│   │       └── Layout.tsx
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── Dockerfile
├── docker-compose.yml
├── README.md
└── .gitignore
```

## 任务清单（TDD）

### Task 1: 后端项目初始化
- 创建 backend/ 目录结构
- requirements.txt: fastapi, uvicorn, sqlalchemy, pyarrow, pydantic, pytest, httpx
- app/config.py: 数据目录配置
- app/db.py: SQLite engine + Base + sessionmaker
- app/main.py: FastAPI app + CORS middleware (allow localhost:5173)
- 验证: `cd backend && pip install -r requirements.txt`

### Task 2: 健康检查 API
- tests/test_health.py: 测试 GET /api/health 返回 200 + {"status": "ok"}
- app/routers/health.py: 实现 /api/health
- app/main.py: 注册 health router
- 验证: `cd backend && pytest tests/ -v` 全绿

### Task 3: 回测模型 + API 骨架
- app/models/backtest.py: BacktestResult SQLAlchemy model
  - id, strategy_name, params_json, start_date, end_date,
    annual_return, max_drawdown, sharpe_ratio, equity_curve_json,
    created_at
- app/models/__init__.py: 导出
- tests/test_backtest_api.py: 测试 POST /api/backtest/run 返回任务 ID
- app/routers/backtest.py: POST /api/backtest/run, GET /api/backtest/{id}
- app/services/backtest_service.py: 占位 stub
- app/db.py: create_all on startup
- 验证: `pytest tests/ -v` 全绿

### Task 4: 前端项目初始化
- `npm create vite@latest frontend -- --template react-ts`
- vite.config.ts: proxy /api → localhost:8000
- src/api/client.ts: fetch wrapper
- src/App.tsx: 路由 (/ → Home, /backtest/:id → BacktestDetail)
- src/pages/Home.tsx: 显示 "Stock Strategy Platform" + 占位
- src/pages/BacktestDetail.tsx: 占位
- src/components/Layout.tsx: 基础布局
- 验证: `cd frontend && npm install && npm run dev` 能打开页面

### Task 5: 前后端联调
- Home.tsx: 调 GET /api/health 显示状态
- 验证: 前端页面显示后端健康状态

### Task 6: Docker Compose
- backend/Dockerfile: python:3.11-slim + install + uvicorn
- frontend/Dockerfile: node:20 + npm install + npm run dev (or build)
- docker-compose.yml: backend + frontend services
- 验证: `docker-compose up` 两个服务都跑起来

## 验收标准
- [ ] `cd backend && pytest tests/ -v` 全绿，覆盖率 ≥ 80%
- [ ] `cd frontend && npm run dev` 浏览器能打开
- [ ] 前端 GET /api/health 显示 {"status": "ok"}
- [ ] `docker-compose up` 两端都能访问（可选）
