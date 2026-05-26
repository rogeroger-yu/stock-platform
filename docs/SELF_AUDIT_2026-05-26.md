# 股票策略研发平台 — 系统自检报告

**日期**: 2026-05-26  
**版本**: v0.2.0  
**测试**: 151 passed, 0 failed

---

## 一、能力矩阵

| 能力 | 状态 | 说明 |
|------|------|------|
| 策略创建 | ✅ | POST /api/strategies，持久化到 SQLite |
| 策略修改 | ✅ | PUT /api/strategies/{id}，支持参数/名称/描述更新 |
| 策略删除 | ✅ | DELETE /api/strategies/{id} |
| 策略列表/筛选 | ✅ | GET /api/strategies?type=xxx |
| 开源策略收集 | ✅ | 15 个策略变体，6 大族 |
| 单股回测 | ✅ | BacktestEngine.run_single() |
| 多股组合回测 | ✅ | PortfolioEngine.run() |
| 批量回测+排名 | ✅ | POST /api/backtests/batch，综合评分排序 |
| Walk-Forward 优化 | ✅ | IS/OOS 分割 + 网格搜索 |
| 模拟交易 | ✅ | PaperTradeEngine，下单/持仓/账户 |
| 策略→交易桥接 | ✅ | BacktestTradeBridge，信号监控+自动发单 |
| 回测结果持久化 | ✅ | SQLite 存储，支持查询/对比 |
| 策略类型目录 | ✅ | GET /api/strategy-types |

## 二、策略库

| 族 | 策略 | 类型键 | 来源 |
|----|------|--------|------|
| 趋势跟踪 | 动量策略 | momentum | 自研 |
| 趋势跟踪 | 动量突破 | momentum_breakout | 自研 |
| 均值回归 | 布林带+RSI | mean_reversion | 自研 |
| 均值回归 | 配对交易 | pairs_mean_reversion | 自研 |
| 多因子 | 综合打分 | factor_score | 自研 |
| 趋势跟踪 | MACD 金叉/死叉 | macd | Gerald Appel, 1979 |
| 趋势跟踪 | MACD 柱状图 | macd_histogram | 变体 |
| 突破 | 布林带突破 | bollinger_breakout | John Bollinger |
| 突破 | 布林带收窄 | bollinger_squeeze | 变体 |
| 震荡 | KDJ 金叉/死叉 | kdj | George Lane |
| 震荡 | KDJ 超卖反转 | kdj_reversal | 变体 |
| 突破 | 海龟系统1 | turtle | Dennis & Eckhardt, 1983 |
| 突破 | 海龟系统2 | turtle_system2 | 变体 |
| 均线 | 双均线交叉 | dual_ma | Granville |
| 均线 | 三均线排列 | triple_ma | 变体 |

## 三、API 端点清单

### 策略管理
- `GET /api/strategy-types` — 策略类型目录
- `POST /api/strategies/seed-defaults` — 初始化默认策略
- `GET /api/strategies` — 策略列表
- `GET /api/strategies/{id}` — 策略详情
- `POST /api/strategies` — 创建策略
- `PUT /api/strategies/{id}` — 修改策略
- `DELETE /api/strategies/{id}` — 删除策略

### 回测
- `POST /api/backtests/run` — 运行单策略回测
- `POST /api/backtests/batch` — 批量回测+Top10排名
- `POST /api/backtests/walk-forward` — Walk-Forward 优化
- `GET /api/backtests` — 回测历史
- `GET /api/backtests/{id}` — 回测详情
- `POST /api/backtests/compare` — 策略对比

### 模拟交易
- `POST /api/paper/order` — 手动下单
- `GET /api/paper/account` — 账户状态
- `GET /api/paper/positions` — 持仓查询
- `GET /api/paper/orders` — 订单查询
- `GET /api/paper/trades` — 交易记录
- `POST /api/paper/signals` — 信号转订单建议
- `POST /api/paper/reset` — 重置账户

### 策略桥接
- `POST /api/paper/strategies/activate` — 激活策略监控
- `DELETE /api/paper/strategies/{type}` — 停用策略
- `GET /api/paper/strategies/active` — 已激活策略
- `POST /api/paper/daily-check` — 每日信号检查
- `GET /api/paper/signal-history` — 信号历史
- `POST /api/paper/compare` — 回测 vs 实盘对比

## 四、已知限制 & 优化建议

### 当前限制
1. **数据依赖**: 需要先下载 A 股数据到 data/parquet/ 才能回测
2. **单标的回测**: 批量回测目前用合成数据，需接入真实行情
3. **前端未适配**: 新 API 端点需要前端页面更新
4. **无定时任务**: daily-check 需要外部触发（可用 cron job）
5. **模拟交易无持久化**: PaperTradeEngine 状态在内存中，重启丢失

### 优化建议
1. **P0 — 数据先行**: 运行 `python -m app.data.downloader --sample` 下载样本数据
2. **P0 — 前端适配**: 更新 StrategyList 页面支持 CRUD + 批量回测
3. **P1 — 定时信号检查**: 用 APScheduler 或系统 cron 每日 15:30 自动触发
4. **P1 — 模拟交易持久化**: 将 PaperTradeEngine 状态存入 SQLite
5. **P2 — 多标的批量下载**: 扩展 downloader 支持 Top50 权重股
6. **P2 — 风险管理**: 添加仓位控制、止损止盈、最大持仓限制
7. **P3 — 实盘接入**: 预留 vnpy/QMT 接口（PaperTradeMode 枚举已预留）

## 五、前端需要更新的页面

1. **StrategyList** — 增加创建/编辑/删除策略的 Modal
2. **Home** — 展示策略类型目录 + 一键初始化
3. **新页面: BatchRank** — 批量回测结果 Top10 排名表
4. **新页面: PaperTrade** — 模拟交易 Dashboard（持仓/订单/信号）
5. **Compare** — 适配新 API 返回结构
