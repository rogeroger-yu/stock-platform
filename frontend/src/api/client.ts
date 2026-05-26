import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE || "http://47.97.26.218:8000";

const client = axios.create({
  baseURL: `${API_BASE}/api`,
  timeout: 60000,
  headers: { "Content-Type": "application/json" },
});

// ─── Type Definitions ───────────────────────────────────────────────

export interface Strategy {
  id: number;
  name: string;
  strategy_type: string;
  description: string;
  params: Record<string, unknown>;
  symbols: string[];
  last_annual_return?: number;
  last_sharpe?: number;
  last_max_drawdown?: number;
  last_win_rate?: number;
  backtest_count: number;
  created_at?: string;
  updated_at?: string;
}

export interface StrategyType {
  type: string;
  name: string;
  default_params: Record<string, unknown>;
}

export interface StrategyCreate {
  name: string;
  strategy_type: string;
  description?: string;
  params?: Record<string, unknown>;
  symbols?: string[];
}

export interface StrategyUpdate {
  name?: string;
  description?: string;
  params?: Record<string, unknown>;
  symbols?: string[];
}

export interface BacktestParams {
  strategy_id: number;
  symbols: string[];
  start_date: string;
  end_date: string;
  initial_capital?: number;
  commission?: number;
  slippage?: number;
  param_overrides?: Record<string, unknown>;
}

export interface EquityPoint {
  date: string;
  equity: number;
  benchmark?: number;
}

export interface BacktestResult {
  id: number;
  strategy_name: string;
  strategy_type: string;
  params: Record<string, unknown>;
  symbols: string[];
  start_date: string;
  end_date: string;
  total_return: number;
  annualized_return: number;
  sharpe: number;
  max_drawdown: number;
  calmar: number;
  num_trades: number;
  win_rate: number;
  avg_holding_days: number;
  equity_curve: EquityPoint[];
  monthly_returns: Record<string, unknown>[];
  yearly_returns: Record<string, unknown>[];
}

export interface BatchResult {
  total_strategies: number;
  symbols: string[];
  period: string;
  top_n: number;
  rankings: {
    strategy_id: number;
    strategy_name: string;
    strategy_type: string;
    params: Record<string, unknown>;
    total_return: number;
    annualized_return: number;
    sharpe: number;
    max_drawdown: number;
    win_rate: number;
    num_trades: number;
    composite_score: number;
  }[];
  all_scores: { name: string; score: number }[];
}

// ─── API Functions ──────────────────────────────────────────────────

export const api = {
  // Strategy Types
  async getStrategyTypes(): Promise<StrategyType[]> {
    const { data } = await client.get("/strategy-types");
    return data;
  },

  async seedDefaults(): Promise<{ created: string[]; skipped: string[]; total: number }> {
    const { data } = await client.post("/strategies/seed-defaults");
    return data;
  },

  // Strategy CRUD
  async getStrategies(strategyType?: string): Promise<Strategy[]> {
    const params = strategyType ? { strategy_type: strategyType } : {};
    const { data } = await client.get("/strategies", { params });
    return data;
  },

  async getStrategy(id: number): Promise<Strategy> {
    const { data } = await client.get(`/strategies/${id}`);
    return data;
  },

  async createStrategy(req: StrategyCreate): Promise<Strategy> {
    const { data } = await client.post("/strategies", req);
    return data;
  },

  async updateStrategy(id: number, req: StrategyUpdate): Promise<Strategy> {
    const { data } = await client.put(`/strategies/${id}`, req);
    return data;
  },

  async deleteStrategy(id: number): Promise<void> {
    await client.delete(`/strategies/${id}`);
  },

  // Backtests
  async runBacktest(params: BacktestParams): Promise<BacktestResult> {
    const { data } = await client.post("/backtests/run", params);
    return data;
  },

  async batchRun(params: {
    symbols: string[];
    start_date: string;
    end_date: string;
    top_n?: number;
  }): Promise<BatchResult> {
    const { data } = await client.post("/backtests/batch", params);
    return data;
  },

  async getBacktestResult(id: number): Promise<BacktestResult | undefined> {
    try {
      const { data } = await client.get(`/backtests/${id}`);
      return data;
    } catch {
      return undefined;
    }
  },

  async getBacktestList(): Promise<BacktestResult[]> {
    try {
      const { data } = await client.get("/backtests");
      return data;
    } catch {
      return [];
    }
  },

  async compareBacktests(ids: number[]): Promise<BacktestResult[]> {
    const { data } = await client.post("/backtests/compare", { backtest_ids: ids });
    return data;
  },

  // Paper Trade
  async getPaperAccount(): Promise<Record<string, unknown>> {
    const { data } = await client.get("/paper/account");
    return data;
  },

  async activateStrategy(strategyType: string, params: Record<string, unknown>, symbols: string[]) {
    const { data } = await client.post("/paper/strategies/activate", {
      strategy_type: strategyType,
      params,
      symbols,
    });
    return data;
  },

  async deactivateStrategy(strategyType: string) {
    const { data } = await client.delete(`/paper/strategies/${strategyType}`);
    return data;
  },

  async getActiveStrategies() {
    const { data } = await client.get("/paper/strategies/active");
    return data;
  },

  async dailyCheck(autoExecute = false) {
    const { data } = await client.post("/paper/daily-check", { auto_execute: autoExecute });
    return data;
  },

  async getSignalHistory(limit = 100) {
    const { data } = await client.get("/paper/signal-history", { params: { limit } });
    return data;
  },

  // Data Management
  async getAvailableStocks() {
    const { data } = await client.get("/data/stocks");
    return data;
  },

  async getStockCoverage(symbol: string) {
    const { data } = await client.get(`/data/stocks/${symbol}`);
    return data;
  },
};

export default client;
