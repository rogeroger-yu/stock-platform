import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE || "http://47.97.26.218:8000";

const client = axios.create({
  baseURL: `${API_BASE}/api`,
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// ─── Type Definitions ───────────────────────────────────────────────

export interface Strategy {
  id: string;
  name: string;
  strategy_type: string;
  description: string;
  params: Record<string, unknown>;
}

export interface BacktestParams {
  strategy_id: string;
  start_date: string;
  end_date: string;
  initial_capital?: number;
  commission?: number;
}

export interface EquityPoint {
  date: string;
  equity: number;
  benchmark?: number;
}

export interface BacktestResult {
  strategy_id: string;
  total_return: number;
  annualized_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  total_trades: number;
  equity_curve: EquityPoint[];
}

// ─── API Functions ──────────────────────────────────────────────────

export const api = {
  async getStrategies(): Promise<Strategy[]> {
    const { data } = await client.get("/strategies");
    return data;
  },

  async runBacktest(params: BacktestParams): Promise<BacktestResult> {
    const { data } = await client.post("/backtests/run", params);
    return data;
  },

  async getBacktestResult(id: string): Promise<BacktestResult | undefined> {
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

  async compareBacktests(ids: string[]): Promise<BacktestResult[]> {
    const { data } = await client.post("/backtests/compare", { strategy_ids: ids });
    return data;
  },
};

export default client;
