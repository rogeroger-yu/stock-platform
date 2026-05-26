import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Typography,
  Card,
  Row,
  Col,
  Statistic,
  Descriptions,
  Tag,
  Spin,
  Table,
  Button,
  Empty,
} from "antd";
import {
  ArrowLeftOutlined,
  RiseOutlined,
  FallOutlined,
} from "@ant-design/icons";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
} from "recharts";
import { api, type BacktestResult } from "../api/client";
import type { ColumnsType } from "antd/es/table";

const { Title, Text } = Typography;

interface TradeRecord {
  key: number;
  date: string;
  action: "买入" | "卖出";
  price: number;
  quantity: number;
  pnl: number;
}

function generateMockTrades(count: number): TradeRecord[] {
  const trades: TradeRecord[] = [];
  const baseDate = new Date("2024-01-02");
  for (let i = 0; i < count; i++) {
    const date = new Date(baseDate);
    date.setDate(date.getDate() + Math.floor(i * 3 + Math.random() * 5));
    const isBuy = i % 2 === 0;
    const price = 10 + Math.random() * 90;
    const quantity = Math.floor(100 + Math.random() * 900);
    trades.push({
      key: i,
      date: date.toISOString().slice(0, 10),
      action: isBuy ? "买入" : "卖出",
      price: Math.round(price * 100) / 100,
      quantity,
      pnl: isBuy ? 0 : Math.round((Math.random() - 0.3) * 5000 * 100) / 100,
    });
  }
  return trades;
}

export default function BacktestDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    api
      .getBacktestResult(id)
      .then((r) => setResult(r ?? null))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: 80 }}>
        <Spin size="large" tip="加载中…" />
      </div>
    );
  }

  if (!result) {
    return (
      <Empty description="未找到该回测结果">
        <Button onClick={() => navigate("/strategies")}>返回策略列表</Button>
      </Empty>
    );
  }

  // Prepare monthly returns heatmap data
  const monthlyHeatmapData = (result.monthly_returns ?? []).map((m: any) => ({
    ...m,
    label: `${m.year}-${String(m.month).padStart(2, "0")}`,
  }));

  const yearlyBarData = (result.yearly_returns ?? []).map((y: any) => ({
    year: String(y.year),
    return: y.return,
  }));

  // Mock trades
  const trades = generateMockTrades(result.total_trades);

  const tradeColumns: ColumnsType<TradeRecord> = [
    { title: "日期", dataIndex: "date", key: "date" },
    {
      title: "操作",
      dataIndex: "action",
      key: "action",
      render: (v: string) => (
        <Tag color={v === "买入" ? "green" : "red"}>{v}</Tag>
      ),
    },
    {
      title: "价格",
      dataIndex: "price",
      key: "price",
      render: (v: number) => `¥${v.toFixed(2)}`,
    },
    {
      title: "数量",
      dataIndex: "quantity",
      key: "quantity",
    },
    {
      title: "盈亏",
      dataIndex: "pnl",
      key: "pnl",
      render: (v: number) =>
        v === 0 ? (
          "-"
        ) : (
          <Text style={{ color: v >= 0 ? "#3f8600" : "#cf1322" }}>
            {v >= 0 ? "+" : ""}
            {v.toFixed(2)}
          </Text>
        ),
    },
  ];

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate("/strategies")}
          style={{ marginBottom: 8 }}
        >
          返回
        </Button>
        <Title level={2} style={{ margin: 0 }}>
          {result.strategy_id}
        </Title>
        <Descriptions size="small" style={{ marginTop: 8 }}>
          <Descriptions.Item label="策略 ID">{result.strategy_id}</Descriptions.Item>
          <Descriptions.Item label="总交易次数">
            {result.total_trades}
          </Descriptions.Item>

        </Descriptions>
      </div>

      {/* Core Metrics */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={8} lg={4}>
          <Card size="small">
            <Statistic
              title="年化收益"
              value={result.annualized_return}
              suffix="%"
              prefix={result.annualized_return >= 0 ? <RiseOutlined /> : <FallOutlined />}
              valueStyle={{
                color: result.annualized_return >= 0 ? "#3f8600" : "#cf1322",
              }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <Card size="small">
            <Statistic
              title="总收益"
              value={result.total_return}
              suffix="%"
              valueStyle={{
                color: result.total_return >= 0 ? "#3f8600" : "#cf1322",
              }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <Card size="small">
            <Statistic
              title="夏普比"
              value={result.sharpe_ratio ?? 0}
              valueStyle={{ color: (result.sharpe_ratio ?? 0) >= 1 ? "#3f8600" : "#faad14" }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <Card size="small">
            <Statistic
              title="最大回撤"
              value={result.max_drawdown}
              suffix="%"
              valueStyle={{ color: "#cf1322" }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <Card size="small">
            <Statistic
              title="胜率"
              value={result.win_rate}
              suffix="%"
              valueStyle={{ color: result.win_rate >= 50 ? "#3f8600" : "#faad14" }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <Card size="small">
            <Statistic title="交易次数" value={result.total_trades} />
          </Card>
        </Col>
      </Row>

      {/* Equity Curve */}
      <Card title="净值曲线" style={{ marginBottom: 24 }}>
        <ResponsiveContainer width="100%" height={350}>
          <LineChart data={result.equity_curve}>
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
              formatter={(value: number) => [`¥${value.toFixed(2)}`, "净值"]}
              labelFormatter={(label: string) => `日期: ${label}`}
            />
            <Line
              type="monotone"
              dataKey="equity"
              stroke="#1677ff"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </Card>

      {/* Monthly & Yearly Returns */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={14}>
          <Card title="月度收益（%）" style={{ height: "100%" }}>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={monthlyHeatmapData}>
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
                  formatter={(value: number) => [`${value.toFixed(2)}%`, "收益率"]}
                />
                <Bar dataKey="return" radius={[4, 4, 0, 0]}>
                  {monthlyHeatmapData.map((entry, index) => (
                    <Cell
                      key={index}
                      fill={entry.return >= 0 ? "#3f8600" : "#cf1322"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title="年度收益（%）" style={{ height: "100%" }}>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={yearlyBarData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="year" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip
                  formatter={(value: number) => [`${value.toFixed(2)}%`, "收益率"]}
                />
                <Bar dataKey="return" radius={[4, 4, 0, 0]}>
                  {yearlyBarData.map((entry, index) => (
                    <Cell
                      key={index}
                      fill={
                        parseFloat(entry.return as unknown as string) >= 0
                          ? "#1677ff"
                          : "#cf1322"
                      }
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      {/* Trade Records */}
      <Card title={`交易记录（共 ${trades.length} 笔）`}>
        <Table
          columns={tradeColumns}
          dataSource={trades}
          size="small"
          pagination={{ pageSize: 20 }}
          expandable={{
            expandedRowRender: (record) => (
              <div style={{ padding: "8px 0" }}>
                <Text type="secondary">
                  {record.action === "买入"
                    ? `以 ¥${record.price.toFixed(2)} 买入 ${record.quantity} 股`
                    : `以 ¥${record.price.toFixed(2)} 卖出 ${record.quantity} 股，盈亏 ¥${record.pnl.toFixed(2)}`}
                </Text>
              </div>
            ),
          }}
        />
      </Card>
    </div>
  );
}
