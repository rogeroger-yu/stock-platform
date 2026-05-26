import { useEffect, useState } from "react";
import { Typography, Card, Row, Col, Button, Statistic, Tag, Space, Divider } from "antd";
import {
  RocketOutlined,
  LineChartOutlined,
  BarChartOutlined,
  FundOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { api, type BacktestResult, type Strategy } from "../api/client";

const { Title, Paragraph, Text } = Typography;

const strategyTypeLabels: Record<string, { color: string; label: string }> = {
  momentum: { color: "blue", label: "动量策略" },
  mean_reversion: { color: "green", label: "均值回归" },
  factor_scoring: { color: "purple", label: "因子打分" },
};

export default function Home() {
  const navigate = useNavigate();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [recentBacktests, setRecentBacktests] = useState<BacktestResult[]>([]);

  useEffect(() => {
    api.getStrategies().then(setStrategies);
    api.getBacktestList().then((list) =>
      setRecentBacktests(list.slice(-3).reverse())
    );
  }, []);

  return (
    <div>
      {/* Hero */}
      <div style={{ marginBottom: 32 }}>
        <Title level={2} style={{ marginBottom: 8 }}>
          📈 股票策略研发平台
        </Title>
        <Paragraph type="secondary" style={{ fontSize: 16 }}>
          构建、回测和对比量化交易策略 · 版本 v0.1.0
        </Paragraph>
      </div>

      {/* Strategy Cards */}
      <Title level={4} style={{ marginBottom: 16 }}>
        策略库
      </Title>
      <Row gutter={[16, 16]}>
        {strategies.map((s) => {
          const meta = strategyTypeLabels[s.strategy_type] ?? {
            color: "default",
            label: s.strategy_type,
          };
          return (
            <Col xs={24} sm={12} lg={8} key={s.id}>
              <Card
                hoverable
                style={{ height: "100%" }}
                actions={[
                  <Button
                    type="link"
                    key="run"
                    icon={<RocketOutlined />}
                    onClick={() => navigate("/strategies")}
                  >
                    运行回测
                  </Button>,
                ]}
              >
                <Space direction="vertical" size={8} style={{ width: "100%" }}>
                  <Space>
                    <Text strong style={{ fontSize: 16 }}>
                      {s.name}
                    </Text>
                    <Tag color={meta.color}>{meta.label}</Tag>
                  </Space>
                  <Text type="secondary">{s.description}</Text>
                  <Divider style={{ margin: "8px 0" }} />
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    参数概要
                  </Text>
                  <div>
                    {Object.entries(s.params).map(([k, v]) => (
                      <Tag key={k} style={{ marginBottom: 4 }}>
                        {k}: {typeof v === "object" ? JSON.stringify(v) : String(v)}
                      </Tag>
                    ))}
                  </div>
                </Space>
              </Card>
            </Col>
          );
        })}
      </Row>

      {/* Quick Stats */}
      <Divider />
      <Row gutter={16} style={{ marginBottom: 32 }}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="策略数量"
              value={strategies.length}
              prefix={<FundOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="回测次数"
              value={recentBacktests.length}
              prefix={<BarChartOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="数据源"
              value="akshare"
              prefix={<LineChartOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="支持市场" value="A股" />
          </Card>
        </Col>
      </Row>

      {/* Recent Backtests */}
      {recentBacktests.length > 0 && (
        <>
          <Title level={4} style={{ marginBottom: 16 }}>
            最近回测结果
          </Title>
          <Row gutter={[16, 16]}>
            {recentBacktests.map((bt) => (
              <Col xs={24} sm={12} lg={8} key={bt.id}>
                <Card
                  size="small"
                  hoverable
                  onClick={() => navigate(`/backtest/${bt.id}`)}
                  style={{ cursor: "pointer" }}
                >
                  <Space direction="vertical" size={4} style={{ width: "100%" }}>
                    <Text strong>{bt.strategy_name}</Text>
                    <Row gutter={8}>
                      <Col span={12}>
                        <Statistic
                          title="年化收益"
                          value={bt.annualized_return ?? 0}
                          suffix="%"
                          valueStyle={{
                            fontSize: 16,
                            color: bt.annualized_return >= 0 ? "#3f8600" : "#cf1322",
                          }}
                        />
                      </Col>
                      <Col span={12}>
                        <Statistic
                          title="夏普比"
                          value={bt.sharpe_ratio ?? 0}
                          valueStyle={{ fontSize: 16 }}
                        />
                      </Col>
                    </Row>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {bt.start_date} ~ {bt.end_date}
                    </Text>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
        </>
      )}

      {/* CTA */}
      <div style={{ textAlign: "center", marginTop: 48 }}>
        <Button
          type="primary"
          size="large"
          icon={<RocketOutlined />}
          onClick={() => navigate("/strategies")}
        >
          开始回测
        </Button>
      </div>
    </div>
  );
}
