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

export default function BacktestDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    api
      .getBacktestResult(Number(id))
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

  const monthlyHeatmapData = (result.monthly_returns ?? []).map((m: any) => ({
    ...m,
    label: `${m.year}-${String(m.month).padStart(2, "0")}`,
    return: (m.return ?? 0) * 100,
  }));

  const yearlyBarData = (result.yearly_returns ?? []).map((y: any) => ({
    year: String(y.year),
    return: (y.return ?? 0) * 100,
  }));

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
          {result.strategy_name}
        </Title>
        <Descriptions size="small" style={{ marginTop: 8 }}>
          <Descriptions.Item label="回测 ID">#{result.id}</Descriptions.Item>
          <Descriptions.Item label="策略类型">
            <Tag>{result.strategy_type}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="标的">
            {result.symbols?.join(", ") || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="区间">
            {result.start_date} ~ {result.end_date}
          </Descriptions.Item>
          <Descriptions.Item label="交易次数">{result.num_trades}</Descriptions.Item>
        </Descriptions>
      </div>

      {/* Core Metrics */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={8} lg={4}>
          <Card size="small">
            <Statistic
              title="年化收益"
              value={((result.annualized_return ?? 0) * 100).toFixed(2)}
              suffix="%"
              prefix={(result.annualized_return ?? 0) >= 0 ? <RiseOutlined /> : <FallOutlined />}
              valueStyle={{
                color: (result.annualized_return ?? 0) >= 0 ? "#3f8600" : "#cf1322",
              }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <Card size="small">
            <Statistic
              title="总收益"
              value={((result.total_return ?? 0) * 100).toFixed(2)}
              suffix="%"
              valueStyle={{
                color: (result.total_return ?? 0) >= 0 ? "#3f8600" : "#cf1322",
              }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <Card size="small">
            <Statistic
              title="夏普比"
              value={(result.sharpe ?? 0).toFixed(2)}
              valueStyle={{ color: (result.sharpe ?? 0) >= 1 ? "#3f8600" : "#faad14" }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <Card size="small">
            <Statistic
              title="最大回撤"
              value={((result.max_drawdown ?? 0) * 100).toFixed(2)}
              suffix="%"
              valueStyle={{ color: "#cf1322" }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <Card size="small">
            <Statistic
              title="胜率"
              value={((result.win_rate ?? 0) * 100).toFixed(1)}
              suffix="%"
              valueStyle={{ color: (result.win_rate ?? 0) >= 0.5 ? "#3f8600" : "#faad14" }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <Card size="small">
            <Statistic
              title="Calmar"
              value={(result.calmar ?? 0).toFixed(2)}
              valueStyle={{ fontSize: 16 }}
            />
          </Card>
        </Col>
      </Row>

      {/* Params */}
      {result.params && Object.keys(result.params).length > 0 && (
        <Card title="策略参数" size="small" style={{ marginBottom: 24 }}>
          {Object.entries(result.params).map(([k, v]) => (
            <Tag key={k} style={{ marginBottom: 4 }}>
              {k}: {typeof v === "object" ? JSON.stringify(v) : String(v)}
            </Tag>
          ))}
        </Card>
      )}

      {/* Equity Curve */}
      <Card title="净值曲线" style={{ marginBottom: 24 }}>
        <ResponsiveContainer width="100%" height={350}>
          <LineChart data={result.equity_curve}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11 }}
              tickFormatter={(v: string) => v?.slice(5) ?? ""}
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
                  {monthlyHeatmapData.map((_: any, index: number) => (
                    <Cell
                      key={index}
                      fill={monthlyHeatmapData[index].return >= 0 ? "#3f8600" : "#cf1322"}
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
                  {yearlyBarData.map((_: any, index: number) => (
                    <Cell
                      key={index}
                      fill={yearlyBarData[index].return >= 0 ? "#1677ff" : "#cf1322"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
