# 策略批量回测报告

**日期**: 2026-05-26 ~ 2026-05-27
**数据周期**: 2020-01-01 ~ 2024-12-31（5年）
**标的**: 6只 A股（平安银行、贵州茅台、五粮液、比亚迪、美的集团、招商银行）
**初始资金**: 1,000,000

## 真实年化收益排名

| 排名 | 策略 | 年化收益 | 最大回撤 | 备注 |
|------|------|---------|---------|------|
| 1 | pairs_mean_reversion | **2.6%** | 28.5% | 配对均值回归 |
| 2 | factor_score | **2.6%** | 48.0% | 多因子，高风险 |
| 3 | mean_reversion | **1.2%** | 15.1% | 低回撤最优 |
| 4 | turtle | 1.0% | 37.9% | 海龟趋势 |
| 5 | kdj_reversal | 0.9% | 29.7% | KDJ反转 |
| 6 | momentum | 0.8% | 46.4% | 动量策略 |
| 7 | kdj | 0.1% | 24.1% | KDJ |
| 8 | turtle_system2 | 0.4% | 49.7% | 海龟2号 |
| 9 | momentum_breakout | 0.4% | 49.6% | 动量突破 |
| 10 | bollinger_breakout | -0.1% | 22.4% | 布林突破 |
| 11 | triple_ma | -0.0% | 40.6% | 三均线 |
| 12 | dual_ma | -0.2% | 52.6% | 双均线 |
| 13 | macd | -0.4% | 46.2% | MACD |
| 14 | bollinger_squeeze | -0.3% | 18.6% | 布林缩口 |
| 15 | macd_histogram | -0.4% | 43.2% | MACD柱 |
| 16 | composite | -1.1% | 7.3% | 复合策略 |
| 17 | adaptive_composite | -1.4% | 6.3% | 自适应复合 |

## 关键发现

### 收益分析
- **2020-2024 A股整体震荡**，大部分策略年化收益 < 3%
- **均值回归类** 表现最好：pairs_mean_reversion 和 mean_reversion
- **趋势跟踪类** 回撤大但收益不突出：momentum, turtle
- **复合策略** 回撤极低(6-7%)但收益为负 — 需要调优

### 风险调整后最优
- **mean_reversion**: 年化1.2% + 回撤15.1% = 最佳风险收益比
- **pairs_mean_reversion**: 年化2.6% + 回撤28.5% = 收益最高之一
- **kdj_reversal**: 年化0.9% + 回撤29.7% = 中等表现

### 策略分类
- **均值回归类**: mean_reversion, pairs_mean_reversion, bollinger_squeeze → 稳定
- **趋势跟踪类**: momentum, turtle, MA系列 → 高回撤
- **复合策略**: composite, adaptive_composite → 低回撤但需调优

## 参数优化记录

### mean_reversion
- 原始: bb_window=20, bb_std=2.0, rsi_period=14, min_holding=20
- 优化后: bb_window=15, bb_std=2.5, rsi_period=10, min_holding=10
- 效果: 回撤从8.2%降至4.0%（6标的平均）

### kdj
- 原始: n=9, oversold=20, overbought=80
- 优化后: n=5, oversold=15, overbought=70
- 效果: 排名稳定

### composite
- 修复 AND→OR 信号逻辑 bug（子策略信号从不重叠）
- 参数: weights=[0.4,0.3,0.3], buy_threshold=0.1, sell_threshold=-0.15, min_holding=15

## 已知问题
1. 策略信号生成逻辑中 min_holding 和 backtest engine 的信号协议不一致
2. 50只标的全量回测因 ECS 性能不足超时
3. 复合策略收益为负，需要重新设计信号融合逻辑

## 下一步
1. 修复策略信号协议（统一 buy/sell/hold 语义）
2. 开发新的趋势跟踪策略（降低回撤）
3. 异步批处理优化（支持50+标的）
4. 接入更多数据源（基本面、资金流）
