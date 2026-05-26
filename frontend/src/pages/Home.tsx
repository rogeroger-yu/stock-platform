import { useEffect, useState } from "react";
import {
  Typography,
  Card,
  Row,
  Col,
  Button,
  Statistic,
  Tag,
  Space,
  Divider,
  Empty,
} from "antd";
import {
  RocketOutlined,
  LineChartOutlined,
  BarChartOutlined,
  FundOutlined,
  ExperimentOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { api, type Strategy } from "../api/client";

const { Title, Paragraph, Text } = Typography;

const strategyTypeLabels: Record<string, { color: string; label: string }> = {
  momentum: { color: "blue", label: "动量策略" },
  momentum_breakout: { color: "cyan", label: "动量突破" },
  mean_reversion: { color: "green", label: "均值回归" },
  pairs_mean_reversion: { color: "lime", label: "配对交易" },
  factor_score: { color: "purple", label: "因子打分" },
  macd: { color: "orange", label: "MACD" },
  macd_histogram: { color: "gold", label: "MACD柱" },
  bollinger_breakout: { color: "magenta", label: "布林突破" },
  bollinger_squeeze: { color: "volcano", label: "布林收窄" },
  kdj: { color: "geekblue", label: "KDJ" },
  kdj_reversal: { color: "default", label: "KDJ反转" },
  turtle: { color: "red", label: "海龟" },
  turtle_system2: { color: "gold", label: "海龟二号" },
  dual_ma: { color: "blue", label: "双均线" },
  triple_ma: { color: "green", label: "三均线" },
};

export default function Home() {
  const navigate = useNavigate();
  const [strategies, setStrategies] = useState<Strategy[]>([]);

  useEffect(() => {
    api.getStrategies().then(setStrategies).catch(() => {});
  }, []);

  const handleSeedDefaults = async () => {
    try {
      await api.seedDefaults();
      const data = await api.getStrategies();
      setStrategies(data);
    } catch {}
  };

  const typeCount = new Set(strategies.map((s) => s.strategy_type)).size;

  return (
    <div>
      {/* Hero */}
      <div style={{ marginBottom: 32 }}>
        <Title level={2} style={{ marginBottom: 8 }}>
          📈 股票策略研发平台
        </Title>
        <Paragraph type="secondary" style={{ fontSize: 16 }}>
          构建、回测和对比量化交易策略 · 支持 15 种内置策略 · 批量排名 · 模拟交易
        </Paragraph>
      </div>

      {/* Quick Stats */}
      <Row gutter={16} style={{ marginBottom: 32 }}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="策略数量" value={strategies.length} prefix={<FundOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="策略族" value={typeCount} prefix={<ExperimentOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="数据源" value="akshare" prefix={<LineChartOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="支持市场" value="A股" prefix={<BarChartOutlined />} />
          </Card>
        </Col>
      </Row>

      {/* Strategy Cards */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          策略库
        </Title>
        {strategies.length === 0 && (
          <Button type="primary" icon={<ExperimentOutlined />} onClick={handleSeedDefaults}>
            初始化 15 个默认策略
          </Button>
        )}
      </div>

      {strategies.length === 0 ? (
        <Card>
          <Empty description="暂无策略，点击上方按钮初始化默认策略库" />
        </Card>
      ) : (
        <Row gutter={[16, 16]}>
          {strategies.slice(0, 12).map((s) => {
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
                    <Text type="secondary" style={{ fontSize: 13 }}>
                      {s.description || "暂无描述"}
                    </Text>
                    <Divider style={{ margin: "8px 0" }} />
                    <div>
                      {Object.entries(s.params)
                        .slice(0, 4)
                        .map(([k, v]) => (
                          <Tag key={k} style={{ marginBottom: 4 }}>
                            {k}: {typeof v === "object" ? JSON.stringify(v) : String(v)}
                          </Tag>
                        ))}
                    </div>
                    {s.backtest_count > 0 && (
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        已回测 {s.backtest_count} 次
                        {s.last_annual_return != null &&
                          ` · 年化 ${(s.last_annual_return * 100).toFixed(1)}%`}
                      </Text>
                    )}
                  </Space>
                </Card>
              </Col>
            );
          })}
        </Row>
      )}

      {strategies.length > 12 && (
        <div style={{ textAlign: "center", marginTop: 16 }}>
          <Button onClick={() => navigate("/strategies")}>
            查看全部 {strategies.length} 个策略
          </Button>
        </div>
      )}

      {/* CTA */}
      <div style={{ textAlign: "center", marginTop: 48 }}>
        <Space>
          <Button
            type="primary"
            size="large"
            icon={<RocketOutlined />}
            onClick={() => navigate("/strategies")}
          >
            策略管理
          </Button>
          <Button
            size="large"
            icon={<BarChartOutlined />}
            onClick={() => navigate("/compare")}
          >
            策略对比
          </Button>
        </Space>
      </div>
    </div>
  );
}
