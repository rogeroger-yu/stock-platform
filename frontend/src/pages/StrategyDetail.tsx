import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Typography,
  Card,
  Descriptions,
  Tag,
  Button,
  Space,
  Form,
  Input,
  InputNumber,
  Select,
  Modal,
  message,
  Spin,
  Divider,
  Table,
  Empty,
  Row,
  Col,
  Statistic,
  Popconfirm,
} from "antd";
import {
  EditOutlined,
  RocketOutlined,
  ArrowLeftOutlined,
  DeleteOutlined,
  ExperimentOutlined,
} from "@ant-design/icons";
import { api, type Strategy, type BacktestResult } from "../api/client";

const { Title, Text, Paragraph } = Typography;

const strategyTypeColors: Record<string, string> = {
  momentum: "blue",
  momentum_breakout: "cyan",
  mean_reversion: "green",
  pairs_mean_reversion: "lime",
  factor_score: "purple",
  macd: "orange",
  macd_histogram: "gold",
  bollinger_breakout: "magenta",
  bollinger_squeeze: "volcano",
  kdj: "geekblue",
  kdj_reversal: "default",
  turtle: "red",
  turtle_system2: "gold",
  dual_ma: "blue",
  triple_ma: "green",
  composite: "purple",
  adaptive_composite: "magenta",
};

const strategyTypeLabels: Record<string, string> = {
  momentum: "动量策略",
  momentum_breakout: "动量突破",
  mean_reversion: "均值回归",
  pairs_mean_reversion: "配对交易",
  factor_score: "因子打分",
  macd: "MACD",
  macd_histogram: "MACD柱",
  bollinger_breakout: "布林突破",
  bollinger_squeeze: "布林收窄",
  kdj: "KDJ",
  kdj_reversal: "KDJ反转",
  turtle: "海龟",
  turtle_system2: "海龟二号",
  dual_ma: "双均线",
  triple_ma: "三均线",
  composite: "复合策略",
  adaptive_composite: "自适应复合",
};

export default function StrategyDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [strategy, setStrategy] = useState<Strategy | null>(null);
  const [loading, setLoading] = useState(true);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [backtestModalOpen, setBacktestModalOpen] = useState(false);
  const [backtestHistory, setBacktestHistory] = useState<BacktestResult[]>([]);
  const [running, setRunning] = useState(false);
  const [editForm] = Form.useForm();
  const [backtestForm] = Form.useForm();

  const fetchStrategy = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await api.getStrategy(Number(id));
      setStrategy(data);
    } catch {
      message.error("策略不存在");
      navigate("/strategies");
    } finally {
      setLoading(false);
    }
  }, [id, navigate]);

  const fetchBacktestHistory = useCallback(async () => {
    try {
      const all = await api.getBacktestList();
      const filtered = all.filter(
        (b) => b.params?.strategy_type === strategy?.strategy_type
      );
      setBacktestHistory(filtered as BacktestResult[]);
    } catch {
      // ignore
    }
  }, [strategy?.strategy_type]);

  useEffect(() => {
    fetchStrategy();
  }, [fetchStrategy]);

  useEffect(() => {
    if (strategy) fetchBacktestHistory();
  }, [strategy, fetchBacktestHistory]);

  const handleEdit = () => {
    if (!strategy) return;
    editForm.setFieldsValue({
      name: strategy.name,
      description: strategy.description,
      params: JSON.stringify(strategy.params, null, 2),
      symbols: strategy.symbols?.join(", ") || "",
    });
    setEditModalOpen(true);
  };

  const handleUpdate = async () => {
    if (!strategy) return;
    try {
      const values = await editForm.validateFields();
      let params = {};
      try {
        params = JSON.parse(values.params);
      } catch {
        message.error("参数格式错误，请输入合法 JSON");
        return;
      }
      const symbols = values.symbols
        ? values.symbols.split(",").map((s: string) => s.trim()).filter(Boolean)
        : [];
      await api.updateStrategy(strategy.id, {
        name: values.name,
        description: values.description,
        params,
        symbols,
      });
      message.success("策略已更新");
      setEditModalOpen(false);
      fetchStrategy();
    } catch (err) {
      if (err !== false) message.error("更新失败");
    }
  };

  const handleDelete = async () => {
    if (!strategy) return;
    await api.deleteStrategy(strategy.id);
    message.success("策略已删除");
    navigate("/strategies");
  };

  const handleRunBacktest = () => {
    if (!strategy) return;
    backtestForm.setFieldsValue({
      symbols: strategy.symbols?.join(", ") || "000001",
      start_date: "2020-01-01",
      end_date: "2025-05-01",
      initial_capital: 1000000,
    });
    setBacktestModalOpen(true);
  };

  const handleSubmitBacktest = async () => {
    if (!strategy) return;
    try {
      const values = await backtestForm.validateFields();
      setRunning(true);
      const symbols = (values.symbols as string)
        .split(",")
        .map((s: string) => s.trim())
        .filter(Boolean);
      const result = await api.runBacktest({
        strategy_id: strategy.id,
        symbols,
        start_date: values.start_date,
        end_date: values.end_date,
        initial_capital: values.initial_capital || 1_000_000,
      });
      message.success(
        `回测完成！年化收益: ${(result.annualized_return * 100).toFixed(2)}%`
      );
      setBacktestModalOpen(false);
      fetchStrategy();
      navigate(`/backtest/${result.id}`);
    } catch (err) {
      if (err !== false) message.error("回测失败");
    } finally {
      setRunning(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!strategy) return null;

  const meta = strategyTypeLabels[strategy.strategy_type] || strategy.strategy_type;
  const color = strategyTypeColors[strategy.strategy_type] || "default";

  const backtestColumns = [
    {
      title: "日期范围",
      key: "period",
      render: (_: unknown, r: BacktestResult) =>
        `${r.start_date || r.params?.start_date || ""} ~ ${r.end_date || r.params?.end_date || ""}`,
    },
    {
      title: "年化收益",
      dataIndex: "annualized_return",
      key: "annualized_return",
      render: (v: number) =>
        v != null ? (
          <Text style={{ color: v >= 0 ? "#3f8600" : "#cf1322" }}>
            {(v * 100).toFixed(2)}%
          </Text>
        ) : (
          "-"
        ),
    },
    {
      title: "Sharpe",
      dataIndex: "sharpe",
      key: "sharpe",
      render: (v: number) => (v != null ? v.toFixed(2) : "-"),
    },
    {
      title: "最大回撤",
      dataIndex: "max_drawdown",
      key: "max_drawdown",
      render: (v: number) =>
        v != null ? (
          <Text style={{ color: "#cf1322" }}>{(v * 100).toFixed(2)}%</Text>
        ) : (
          "-"
        ),
    },
    {
      title: "操作",
      key: "action",
      render: (_: unknown, r: BacktestResult) => (
        <Button
          type="link"
          size="small"
          onClick={() => navigate(`/backtest/${r.id}`)}
        >
          查看详情
        </Button>
      ),
    },
  ];

  return (
    <div>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 24,
        }}
      >
        <Space>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate("/strategies")}
          >
            返回列表
          </Button>
          <Title level={3} style={{ margin: 0 }}>
            {strategy.name}
          </Title>
          <Tag color={color}>{meta}</Tag>
        </Space>
        <Space>
          <Button
            type="primary"
            icon={<RocketOutlined />}
            onClick={handleRunBacktest}
          >
            运行回测
          </Button>
          <Button icon={<EditOutlined />} onClick={handleEdit}>
            编辑
          </Button>
          <Popconfirm
            title="确定删除此策略？删除后不可恢复。"
            onConfirm={handleDelete}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      </div>

      <Row gutter={24}>
        {/* Left: Strategy Info */}
        <Col xs={24} lg={16}>
          <Card title="策略信息" style={{ marginBottom: 24 }}>
            <Descriptions column={{ xs: 1, sm: 2 }} bordered size="small">
              <Descriptions.Item label="策略名称">
                {strategy.name}
              </Descriptions.Item>
              <Descriptions.Item label="策略类型">
                <Tag color={color}>{meta}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>
                {strategy.description || <Text type="secondary">暂无描述</Text>}
              </Descriptions.Item>
              <Descriptions.Item label="跟踪标的" span={2}>
                {strategy.symbols?.length > 0
                  ? strategy.symbols.map((s) => (
                      <Tag key={s} style={{ marginBottom: 4 }}>
                        {s}
                      </Tag>
                    ))
                  : <Text type="secondary">未设置</Text>}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {strategy.created_at
                  ? new Date(strategy.created_at).toLocaleString("zh-CN")
                  : "-"}
              </Descriptions.Item>
              <Descriptions.Item label="更新时间">
                {strategy.updated_at
                  ? new Date(strategy.updated_at).toLocaleString("zh-CN")
                  : "-"}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          {/* Parameters */}
          <Card title="策略参数" style={{ marginBottom: 24 }}>
            {Object.keys(strategy.params || {}).length > 0 ? (
              <Descriptions column={{ xs: 1, sm: 2 }} bordered size="small">
                {Object.entries(strategy.params).map(([key, value]) => (
                  <Descriptions.Item key={key} label={key}>
                    <Text code>
                      {typeof value === "object"
                        ? JSON.stringify(value)
                        : String(value)}
                    </Text>
                  </Descriptions.Item>
                ))}
              </Descriptions>
            ) : (
              <Empty description="暂无参数" />
            )}
          </Card>

          {/* Backtest History */}
          <Card
            title="回测历史"
            extra={
              <Button
                size="small"
                icon={<ExperimentOutlined />}
                onClick={fetchBacktestHistory}
              >
                刷新
              </Button>
            }
          >
            {backtestHistory.length > 0 ? (
              <Table
                columns={backtestColumns}
                dataSource={backtestHistory}
                rowKey="id"
                size="small"
                pagination={{ pageSize: 10 }}
              />
            ) : (
              <Empty description="暂无回测记录" />
            )}
          </Card>
        </Col>

        {/* Right: Metrics Summary */}
        <Col xs={24} lg={8}>
          <Card title="最近回测指标" style={{ marginBottom: 24 }}>
            {strategy.backtest_count > 0 ? (
              <Space direction="vertical" style={{ width: "100%" }} size={16}>
                <Statistic
                  title="年化收益率"
                  value={
                    strategy.last_annual_return != null
                      ? (strategy.last_annual_return * 100).toFixed(2)
                      : "-"
                  }
                  suffix="%"
                  valueStyle={{
                    color:
                      (strategy.last_annual_return ?? 0) >= 0
                        ? "#3f8600"
                        : "#cf1322",
                  }}
                />
                <Statistic
                  title="Sharpe 比率"
                  value={
                    strategy.last_sharpe != null
                      ? strategy.last_sharpe.toFixed(2)
                      : "-"
                  }
                />
                <Statistic
                  title="最大回撤"
                  value={
                    strategy.last_max_drawdown != null
                      ? (strategy.last_max_drawdown * 100).toFixed(2)
                      : "-"
                  }
                  suffix="%"
                  valueStyle={{ color: "#cf1322" }}
                />
                <Statistic
                  title="胜率"
                  value={
                    strategy.last_win_rate != null
                      ? (strategy.last_win_rate * 100).toFixed(1)
                      : "-"
                  }
                  suffix="%"
                />
                <Divider />
                <Statistic
                  title="回测次数"
                  value={strategy.backtest_count}
                  prefix={<ExperimentOutlined />}
                />
              </Space>
            ) : (
              <Empty description="尚未运行回测">
                <Button
                  type="primary"
                  icon={<RocketOutlined />}
                  onClick={handleRunBacktest}
                >
                  立即回测
                </Button>
              </Empty>
            )}
          </Card>

          {/* Quick Actions */}
          <Card title="快捷操作">
            <Space direction="vertical" style={{ width: "100%" }}>
              <Button
                block
                type="primary"
                icon={<RocketOutlined />}
                onClick={handleRunBacktest}
              >
                运行回测
              </Button>
              <Button
                block
                icon={<EditOutlined />}
                onClick={handleEdit}
              >
                编辑参数
              </Button>
              <Button
                block
                onClick={() => navigate("/compare")}
              >
                策略对比
              </Button>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* Edit Modal */}
      <Modal
        title={`编辑策略 — ${strategy.name}`}
        open={editModalOpen}
        onOk={handleUpdate}
        onCancel={() => setEditModalOpen(false)}
        okText="保存"
        cancelText="取消"
        width={700}
      >
        <Form form={editForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item label="策略名称" name="name">
            <Input />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item label="跟踪标的（逗号分隔）" name="symbols">
            <Input placeholder="000001, 600519, 000858" />
          </Form.Item>
          <Form.Item label="参数（JSON）" name="params">
            <Input.TextArea rows={8} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Backtest Modal */}
      <Modal
        title={`运行回测 — ${strategy.name}`}
        open={backtestModalOpen}
        onOk={handleSubmitBacktest}
        onCancel={() => setBacktestModalOpen(false)}
        confirmLoading={running}
        okText="开始回测"
        cancelText="取消"
        width={500}
      >
        <Form form={backtestForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            label="股票代码（逗号分隔）"
            name="symbols"
            rules={[{ required: true, message: "请输入股票代码" }]}
          >
            <Input placeholder="000001,600519,000858" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="开始日期"
                name="start_date"
                rules={[{ required: true }]}
              >
                <Input placeholder="2020-01-01" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="结束日期"
                name="end_date"
                rules={[{ required: true }]}
              >
                <Input placeholder="2025-05-01" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="初始资金" name="initial_capital">
            <InputNumber style={{ width: "100%" }} min={10000} step={100000} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
