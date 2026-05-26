import { useState } from "react";
import {
  Typography,
  Card,
  Form,
  Input,
  InputNumber,
  Button,
  Table,
  Space,
  Tag,
  Row,
  Col,
  Statistic,
  Empty,
  message,
} from "antd";
import {
  ThunderboltOutlined,
  TrophyOutlined,
  RiseOutlined,
  FallOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { api, type BatchResult } from "../api/client";
import type { ColumnsType } from "antd/es/table";

const { Title, Paragraph, Text } = Typography;

export default function BatchRun() {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BatchResult | null>(null);

  const handleRun = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      const symbols = (values.symbols as string)
        .split(",")
        .map((s: string) => s.trim())
        .filter(Boolean);
      const data = await api.batchRun({
        symbols,
        start_date: values.start_date,
        end_date: values.end_date,
        top_n: values.top_n || 10,
      });
      setResult(data);
      message.success(`批量回测完成！${data.total_strategies} 个策略`);
    } catch (err) {
      if (err !== false) message.error("批量回测失败");
    } finally {
      setLoading(false);
    }
  };

  const columns: ColumnsType<BatchResult["rankings"][0]> = [
    {
      title: "排名",
      key: "rank",
      width: 60,
      render: (_: unknown, __: unknown, index: number) => {
        const medals = ["🥇", "🥈", "🥉"];
        return medals[index] || `#${index + 1}`;
      },
    },
    {
      title: "策略名称",
      dataIndex: "strategy_name",
      key: "name",
      render: (v: string) => <Text strong>{v}</Text>,
    },
    {
      title: "策略类型",
      dataIndex: "strategy_type",
      key: "type",
      render: (v: string) => <Tag>{v}</Tag>,
    },
    {
      title: "综合得分",
      dataIndex: "composite_score",
      key: "score",
      render: (v: number) => (
        <Text strong style={{ color: "#1677ff" }}>
          {v.toFixed(4)}
        </Text>
      ),
      sorter: (a, b) => a.composite_score - b.composite_score,
    },
    {
      title: "年化收益",
      dataIndex: "annualized_return",
      key: "ar",
      render: (v: number) => (
        <Text style={{ color: v >= 0 ? "#3f8600" : "#cf1322" }}>
          {(v * 100).toFixed(2)}%
        </Text>
      ),
      sorter: (a, b) => a.annualized_return - b.annualized_return,
    },
    {
      title: "Sharpe",
      dataIndex: "sharpe",
      key: "sharpe",
      render: (v: number) => v.toFixed(2),
      sorter: (a, b) => a.sharpe - b.sharpe,
    },
    {
      title: "最大回撤",
      dataIndex: "max_drawdown",
      key: "mdd",
      render: (v: number) => (
        <Text style={{ color: "#cf1322" }}>{(v * 100).toFixed(2)}%</Text>
      ),
      sorter: (a, b) => a.max_drawdown - b.max_drawdown,
    },
    {
      title: "胜率",
      dataIndex: "win_rate",
      key: "wr",
      render: (v: number) => `${(v * 100).toFixed(1)}%`,
    },
    {
      title: "交易次数",
      dataIndex: "num_trades",
      key: "nt",
    },
  ];

  const best = result?.rankings?.[0];

  return (
    <div>
      <Title level={2}>🏆 批量回测排名</Title>
      <Paragraph type="secondary">
        对所有策略进行批量回测，按综合得分排名
      </Paragraph>

      <Card style={{ marginBottom: 24 }}>
        <Form form={form} layout="inline" style={{ flexWrap: "wrap", gap: 8 }}>
          <Form.Item
            label="股票代码"
            name="symbols"
            rules={[{ required: true }]}
            initialValue="000001,600519,000858"
            style={{ flex: 2, minWidth: 200 }}
          >
            <Input placeholder="000001,600519,000858" />
          </Form.Item>
          <Form.Item
            label="开始日期"
            name="start_date"
            rules={[{ required: true }]}
            initialValue="2020-01-01"
          >
            <Input placeholder="2020-01-01" style={{ width: 130 }} />
          </Form.Item>
          <Form.Item
            label="结束日期"
            name="end_date"
            rules={[{ required: true }]}
            initialValue="2025-01-01"
          >
            <Input placeholder="2025-01-01" style={{ width: 130 }} />
          </Form.Item>
          <Form.Item label="Top N" name="top_n" initialValue={10}>
            <InputNumber min={1} max={50} style={{ width: 80 }} />
          </Form.Item>
          <Form.Item>
            <Button
              type="primary"
              icon={<ThunderboltOutlined />}
              onClick={handleRun}
              loading={loading}
            >
              开始批量回测
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {!result && (
        <Card>
          <Empty description="配置参数后点击「开始批量回测」" />
        </Card>
      )}

      {result && (
        <>
          {/* Best Strategy Banner */}
          {best && (
            <Card
              style={{
                marginBottom: 24,
                background: "linear-gradient(135deg, #fff7e6 0%, #f6ffed 100%)",
                border: "1px solid #ffe58f",
              }}
            >
              <Row gutter={24} align="middle">
                <Col>
                  <TrophyOutlined style={{ fontSize: 48, color: "#faad14" }} />
                </Col>
                <Col flex="auto">
                  <Title level={4} style={{ margin: 0 }}>
                    🏆 最优策略：{best.strategy_name}
                  </Title>
                  <Text type="secondary">
                    综合得分 {best.composite_score.toFixed(4)} · 年化{" "}
                    {(best.annualized_return * 100).toFixed(2)}% · Sharpe{" "}
                    {best.sharpe.toFixed(2)} · 回撤{" "}
                    {(best.max_drawdown * 100).toFixed(2)}%
                  </Text>
                </Col>
              </Row>
            </Card>
          )}

          {/* Summary Stats */}
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col xs={12} sm={6}>
              <Card size="small">
                <Statistic
                  title="策略总数"
                  value={result.total_strategies}
                  prefix={<ThunderboltOutlined />}
                />
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card size="small">
                <Statistic
                  title="回测标的"
                  value={result.symbols.length}
                  suffix="只"
                />
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card size="small">
                <Statistic
                  title="最优年化"
                  value={best ? (best.annualized_return * 100).toFixed(2) : "-"}
                  suffix="%"
                  prefix={<RiseOutlined />}
                  valueStyle={{ color: "#3f8600" }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card size="small">
                <Statistic
                  title="最优 Sharpe"
                  value={best ? best.sharpe.toFixed(2) : "-"}
                />
              </Card>
            </Col>
          </Row>

          {/* Rankings Table */}
          <Card title="策略排名">
            <Table
              columns={columns}
              dataSource={result.rankings}
              rowKey="strategy_id"
              pagination={false}
              size="middle"
            />
          </Card>
        </>
      )}
    </div>
  );
}
