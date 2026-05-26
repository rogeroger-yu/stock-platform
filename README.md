# 📈 股票策略研发平台

量化交易策略的构建、回测和对比分析平台。

## 技术栈

- **后端**: FastAPI + Pandas + akshare
- **前端**: React 18 + TypeScript + Vite + Ant Design + Recharts
- **部署**: Docker Compose

## 快速开始

```bash
# 启动开发环境
make dev

# 仅启动后端（本地开发）
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload

# 仅启动前端（本地开发）
cd frontend && npm install && npm run dev
```

## 运行测试

```bash
make test
```

## API 文档

启动后端后访问: http://localhost:8000/docs

## 项目结构

```
stock-platform/
├── backend/          # FastAPI 后端
├── frontend/         # React 前端
├── docker-compose.yml
├── Makefile
└── README.md
```
