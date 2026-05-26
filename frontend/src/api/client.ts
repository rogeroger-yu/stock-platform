import axios from "axios";

const client = axios.create({
  baseURL: "/api",
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// ─── Type Definitions ───────────────────────────────────────────────

export interface Strategy {
  id: string;
  name: string;
  type: "momentum" | "mean_reversion" | "factor_scoring";
  description: string;
  params: Record<string, unknown>;
}

export interface BacktestParams {
  strategy: string;
  params: Record<string, unknown>;
  start_date: string;
  end_date: string;
  symbols?: string[];
}

export interface EquityPoint {
  date: string;
  equity: number;
  returns: number;
}

export interface MonthlyReturn {
  year: number;
  month: number;
  return: number;
}

export interface YearlyReturn {
  year: number;
  return: number;
}

export interface BacktestResult {
  id: string;
  strategy_name: string;
  strategy_params: Record<string, unknown>;
  total_return: number;
  annualized_return: number;
  sharpe: number;
  max_drawdown: number;
  win_rate: number;
  num_trades: number;
  equity_curve: EquityPoint[];
  monthly_returns: MonthlyReturn[];
  yearly_returns: YearlyReturn[];
  status: "running" | "completed" | "failed";
  start_date: string;
  end_date: string;
}

// ─── Mock Data ──────────────────────────────────────────────────────

const MOCK_STRATEGIES: Strategy[] = [
  {
    id: "momentum-1",
    name: "动量突破策略",
    type: "momentum",
    description: "基于价格动量和成交量突破的趋势跟踪策略，适合牛市行情",
    params: { lookback_days: 20, volume_multiplier: 1.5, stop_loss: 0.05 },
  },
  {
    id: "mean-reversion-1",
    name: "布林带均值回归",
    type: "mean_reversion",
    description: "利用布林带和RSI识别超卖反弹机会，在震荡市中表现优异",
    params: { bb_period: 20, bb_std: 2, rsi_period: 14, rsi_threshold: 30 },
  },
  {
    id: "factor-scoring-1",
    name: "多因子打分策略",
    type: "factor_scoring",
    description: "综合PE、ROE、动量等多因子打分选股，兼顾价值和成长",
    params: { factors: ["pe", "roe", "momentum"], top_n: 10, rebalance_days: 20 },
  },
  {
    id: "momentum-2",
    name: "均线金叉策略",
    type: "momentum",
    description: "经典双均线交叉系统，配合ATR止损控制回撤",
    params: { fast_ma: 5, slow_ma: 20, atr_period: 14, atr_multiplier: 2 },
  },
];

function generateEquityCurve(startEquity: number, days: number): EquityPoint[] {
  const curve: EquityPoint[] = [];
  let equity = startEquity;
  const startDate = new Date("2024-01-02");
  for (let i = 0; i < days; i++) {
    const date = new Date(startDate);
    date.setDate(date.getDate() + i);
    const dailyReturn = (Math.random() - 0.48) * 0.03;
    equity *= 1 + dailyReturn;
    curve.push({
      date: date.toISOString().slice(0, 10),
      equity: Math.round(equity * 100) / 100,
      returns: Math.round(dailyReturn * 10000) / 10000,
    });
  }
  return curve;
}

function generateMonthlyReturns(year: number): MonthlyReturn[] {
  const months: MonthlyReturn[] = [];
  for (let m = 1; m <= 12; m++) {
    months.push({
      year,
      month: m,
      return: Math.round((Math.random() - 0.45) * 10 * 100) / 100,
    });
  }
  return months;
}

function generateYearlyReturns(): YearlyReturn[] {
  return [
    { year: 2022, return: Math.round((Math.random() - 0.3) * 40 * 100) / 100 },
    { year: 2023, return: Math.round((Math.random() - 0.3) * 40 * 100) / 100 },
    { year: 2024, return: Math.round((Math.random() - 0.3) * 40 * 100) / 100 },
    { year: 2025, return: Math.round((Math.random() - 0.3) * 40 * 100) / 100 },
  ];
}

let mockBacktestCounter = 0;
const mockBacktestResults = new Map<string, BacktestResult>();

function createMockBacktest(strategyId: string, params: BacktestParams): BacktestResult {
  const strategy = MOCK_STRATEGIES.find((s) => s.id === strategyId);
  const id = `bt-${++mockBacktestCounter}`;
  const equityCurve = generateEquityCurve(100000, 240);
  const finalEquity = equityCurve[equityCurve.length - 1].equity;
  const totalReturn = ((finalEquity - 100000) / 100000) * 100;

  const result: BacktestResult = {
    id,
    strategy_name: strategy?.name ?? strategyId,
    strategy_params: params.params,
    total_return: Math.round(totalReturn * 100) / 100,
    annualized_return: Math.round(totalReturn * 0.85 * 100) / 100,
    sharpe: Math.round((0.5 + Math.random() * 2) * 100) / 100,
    max_drawdown: Math.round((-5 - Math.random() * 25) * 100) / 100,
    win_rate: Math.round((45 + Math.random() * 20) * 100) / 100,
    num_trades: Math.floor(50 + Math.random() * 200),
    equity_curve: equityCurve,
    monthly_returns: [...generateMonthlyReturns(2024), ...generateMonthlyReturns(2025)],
    yearly_returns: generateYearlyReturns(),
    status: "completed",
    start_date: params.start_date,
    end_date: params.end_date,
  };

  mockBacktestResults.set(id, result);
  return result;
}

// Pre-seed some backtest results
createMockBacktest("momentum-1", {
  strategy: "momentum-1",
  params: { lookback_days: 20, volume_multiplier: 1.5, stop_loss: 0.05 },
  start_date: "2024-01-01",
  end_date: "2025-12-31",
});
createMockBacktest("mean-reversion-1", {
  strategy: "mean-reversion-1",
  params: { bb_period: 20, bb_std: 2, rsi_period: 14, rsi_threshold: 30 },
  start_date: "2024-01-01",
  end_date: "2025-12-31",
});
createMockBacktest("factor-scoring-1", {
  strategy: "factor-scoring-1",
  params: { factors: ["pe", "roe", "momentum"], top_n: 10, rebalance_days: 20 },
  start_date: "2024-01-01",
  end_date: "2025-12-31",
});

// ─── API Functions (mock) ───────────────────────────────────────────

/** Simulate network delay */
const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const api = {
  async getStrategies(): Promise<Strategy[]> {
    await delay(200);
    return MOCK_STRATEGIES;
  },

  async runBacktest(params: BacktestParams): Promise<BacktestResult> {
    await delay(800);
    return createMockBacktest(params.strategy, params);
  },

  async getBacktestResult(id: string): Promise<BacktestResult | undefined> {
    await delay(200);
    return mockBacktestResults.get(id);
  },

  async getBacktestList(): Promise<BacktestResult[]> {
    await delay(300);
    return Array.from(mockBacktestResults.values());
  },

  async compareBacktests(ids: string[]): Promise<BacktestResult[]> {
    await delay(300);
    return ids
      .map((id) => mockBacktestResults.get(id))
      .filter((r): r is BacktestResult => r !== undefined);
  },
};

export default client;
