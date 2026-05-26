import { useEffect, useState } from "react";
import {
  Typography,
  Card,
  Row,
  Col,
  Select,
  Button,
  Table,
  Empty,
  Space,
  Statistic,
  Divider,
} from "antd";
import { SwapOutlined, TrophyOutlined } from "@ant-design/icons";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  BarChart,
  Bar,
} from "recharts";
import { api, type BacktestResult } from "../api/client";
import type { ColumnsType } from "antd/es/table";

const { Title, Text, Paragraph } = Typography;

const COLORS = ["#1677ff", "#3f8600", "#722ed1", "#cf1322"];

export default function Compare() {
  const [allBacktests, setAllBacktests] = useState<BacktestResult[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [results, setResults] = useState<BacktestResult[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.getBacktestList().then(setAllBacktests);
  }, []);

  const handleCompare = async () => {
    if (selectedIds.length < 2) return;
    setLoading(true);
    try {
      const data = await api.compareBacktests(selectedIds);
      setResults(data);
    } finally {
      setLoading(false);
    }
  };

  const bestStrategy =
    results.length > 0
      ? results.reduce((best, curr) =>
          (curr.sharpe_ratio ?? 0) > (best.sharpe_ratio ?? 0) ? curr : best
        )
      : null;

  const buildCombinedEquity = () => {
    if (results.length === 0) return [];
    const baseCurve = results[0].equity_curve;
    return baseCurve.map((point, i) => {
      const entry: Record<string, number | string> = { date: point.date };
      results.forEach((r) => {
        if (r.equity_curve[i]) {
          entry[r.strategy_id] = r.equity_curve[i].equity;
        }
      });
      return entry;
    });
  };

  const buildMonthlyComparison = () => {
    if (results.length === 0) return [];
    const monthMap = new Map<string, Record<string, number | string>>();
    results.forEach((r) => {
      (r.monthly_returns ?? []).forEach((m: any) => {
        const key = `${m.year}-${String(m.month).padStart(2, "0")}`;
        if (!monthMap.has(key)) monthMap.set(key, { label: key });
        monthMap.get(key)![r.strategy_id] = m.return;
      });
    });
    return Array.from(monthMap.values()).sort((a, b) =>
      (a.label as string).localeCompare(b.label as string)
    );
  };

  const combinedEquity = buildCombinedEquity();
  const monthlyComparison = buildMonthlyComparison();

  const compColumns: ColumnsType<BacktestResult> = [
    {
      title: "策略",
      dataIndex: "strategy_id",
      key: "strategy_id",
      render: (v: string) => <Text strong>{v}</Text>,
    },
    {
      title: "年化收益",
      dataIndex: "annualized_return",
      key: "ar",
      render: (v: number) => (
        <Text style={{ color: (v ?? 0) >= 0 ? "#3f8600" : "#cf1322" }}>
          {(v ?? 0).toFixed(2)}%
        </Text>
      ),
    },
    {
      title: "夏普比",
      dataIndex: "sharpe_ratio",
      key: "sharpe_ratio",
      render: (v: number) => (v ?? 0).toFixed(2),
    },
    {
      title: "最大回撤",
      dataIndex: "max_drawdown",
      key: "mdd",
      render: (v: number) => (
        <Text style={{ color: "#cf1322" }}>{(v ?? 0).toFixed(2)}%</Text>
      ),
    },
    {
      title: "胜率",
      dataIndex: "win_rate",
      key: "wr",
      render: (v: number) => `${(v ?? 0).toFixed(1)}%`,
    },
    {
      title: "交易次数",
      dataIndex: "total_trades",
      key: "tt",
    },
    {
      title: "总收益",
      dataIndex: "total_return",
      key: "tr",
      render: (v: number) => (
        <Text style={{ color: (v ?? 0) >= 0 ? "#3f8600" : "#cf1322" }}>
          {(v ?? 0).toFixed(2)}%
        </Text>
      ),
    },
  ];

  return (
    <div>
      <Title level={2}>策略对比</Title>
      <Paragraph type="secondary">
        选择 2–4 个策略进行多维度对比分析
      </Paragraph>

      <Card style={{ marginBottom: 24 }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Select
              mode="multiple"
              placeholder="选择要对比的回测结果"
              value={selectedIds}
              onChange={setSelectedIds}
              style={{ width: "100%" }}
              maxCount={4}
              options={allBacktests.map((b) => ({
                value: b.strategy_id,
                label: b.strategy_id,
              }))}
            />
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<SwapOutlined />}
              onClick={handleCompare}
              disabled={selectedIds.length < 2}
              loading={loading}
            >
              开始对比
            </Button>
          </Col>
        </Row>
      </Card>

      {results.length === 0 && (
        <Card>
          <Empty description="请先选择策略进行对比" />
        </Card>
      )}

      {results.length > 0 && (
        <>
          {bestStrategy && (
            <Card
              style={{
                marginBottom: 24,
                background: "linear-gradient(135deg, #e6f4ff 0%, #f6ffed 100%)",
                border: "1px solid #91caff",
              }}
            >
              <Space>
                <TrophyOutlined style={{ fontSize: 24, color: "#faad14" }} />
                <div>
                  <Text strong style={{ fontSize: 16 }}>
                    最优策略：{bestStrategy.strategy_id}
                  </Text>
                  <br />
                  <Text type="secondary">
                    夏普比 {(bestStrategy.sharpe_ratio ?? 0).toFixed(2)} · 年化{" "}
                    {(bestStrategy.annualized_return ?? 0).toFixed(2)}% · 回撤{" "}
                    {(bestStrategy.max_drawdown ?? 0).toFixed(2)}%
                  </Text>
                </div>
              </Space>
            </Card>
          )}

          <Card title="核心指标对比" style={{ marginBottom: 24 }}>
            <Table
              columns={compColumns}
              dataSource={results}
              rowKey="strategy_id"
              pagination={false}
              size="middle"
            />
          </Card>

          <Card title="净值曲线叠加" style={{ marginBottom: 24 }}>
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={combinedEquity}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v: string) => v.slice(5)}
                />
                <YAxis
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
                />
                <Tooltip
                  formatter={(value: number, name: string) => [
                    `¥${value.toFixed(2)}`,
                    name,
                  ]}
                />
                <Legend />
                {results.map((r, i) => (
                  <Line
                    key={r.strategy_id}
                    type="monotone"
                    dataKey={r.strategy_id}
                    stroke={COLORS[i % COLORS.length]}
                    strokeWidth={2}
                    dot={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </Card>

          <Card title="月度收益对比（%）" style={{ marginBottom: 24 }}>
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={monthlyComparison}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey="label"
                  tick={{ fontSize: 10 }}
                  angle={-45}
                  textAnchor="end"
                  height={60}
                />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip
                  formatter={(value: number, name: string) => [
                    `${value.toFixed(2)}%`,
                    name,
                  ]}
                />
                <Legend />
                {results.map((r, i) => (
                  <Bar
                    key={r.strategy_id}
                    dataKey={r.strategy_id}
                    fill={COLORS[i % COLORS.length]}
                    radius={[2, 2, 0, 0]}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Title level={4} style={{ marginBottom: 16 }}>
            策略详情
          </Title>
          <Row gutter={[16, 16]}>
            {results.map((r, i) => (
              <Col xs={24} sm={12} key={r.strategy_id}>
                <Card
                  size="small"
                  style={{ borderLeft: `4px solid ${COLORS[i % COLORS.length]}` }}
                >
                  <Title level={5}>{r.strategy_id}</Title>
                  <Row gutter={[8, 8]}>
                    <Col span={8}>
                      <Statistic
                        title="年化收益"
                        value={r.annualized_return ?? 0}
                        suffix="%"
                        valueStyle={{ fontSize: 14 }}
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic
                        title="夏普比"
                        value={r.sharpe_ratio ?? 0}
                        valueStyle={{ fontSize: 14 }}
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic
                        title="最大回撤"
                        value={r.max_drawdown ?? 0}
                        suffix="%"
                        valueStyle={{ fontSize: 14, color: "#cf1322" }}
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic
                        title="胜率"
                        value={r.win_rate ?? 0}
                        suffix="%"
                        valueStyle={{ fontSize: 14 }}
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic
                        title="交易次数"
                        value={r.total_trades}
                        valueStyle={{ fontSize: 14 }}
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic
                        title="总收益"
                        value={r.total_return ?? 0}
                        suffix="%"
                        valueStyle={{ fontSize: 14 }}
                      />
                    </Col>
                  </Row>
                </Card>
              </Col>
            ))}
          </Row>
        </>
      )}
    </div>
  );
}
