import { useEffect, useState, useCallback } from "react";
import {
  Typography,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  message,
  Row,
  Col,
} from "antd";
import {
  RocketOutlined,
  EyeOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { api, type Strategy, type BacktestResult, type BacktestParams } from "../api/client";
import type { ColumnsType } from "antd/es/table";

const { Title, Text } = Typography;

const strategyTypeColors: Record<string, string> = {
  momentum: "blue",
  mean_reversion: "green",
  factor_scoring: "purple",
};

const strategyTypeOptions = [
  { label: "全部类型", value: "" },
  { label: "动量策略", value: "momentum" },
  { label: "均值回归", value: "mean_reversion" },
  { label: "因子打分", value: "factor_scoring" },
];

export default function StrategyList() {
  const navigate = useNavigate();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [backtests, setBacktests] = useState<BacktestResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [running, setRunning] = useState(false);
  const [form] = Form.useForm();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [sRes, bRes] = await Promise.all([
        api.getStrategies(),
        api.getBacktestList(),
      ]);
      setStrategies(sRes);
      setBacktests(bRes);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const filteredStrategies = typeFilter
    ? strategies.filter((s) => s.strategy_type === typeFilter)
    : strategies;

  const handleRunBacktest = (strategy: Strategy) => {
    setSelectedStrategy(strategy);
    form.setFieldsValue({
      start_date: "2024-01-01",
      end_date: "2025-12-31",
      ...strategy.params,
    });
    setModalOpen(true);
  };

  const handleSubmitBacktest = async () => {
    if (!selectedStrategy) return;
    try {
      const values = await form.validateFields();
      setRunning(true);

      const { start_date, end_date, symbols, ...restParams } = values;
      const params: BacktestParams = {
        strategy_id: selectedStrategy.id,
        start_date: start_date ?? "2024-01-01",
        end_date: end_date ?? "2025-12-31",
        symbols: symbols
          ? (symbols as string).split(",").map((s: string) => s.trim())
          : undefined,
      };

      const result = await api.runBacktest(params);
      message.success(`回测完成！ID: ${result.id}`);
      setModalOpen(false);
      fetchData();
      navigate(`/backtest/${result.id}`);
    } catch (err) {
      if (err !== false) message.error("回测失败，请检查参数");
    } finally {
      setRunning(false);
    }
  };

  const strategyColumns: ColumnsType<Strategy> = [
    {
      title: "策略名称",
      dataIndex: "name",
      key: "name",
      render: (name: string) => <Text strong>{name}</Text>,
    },
    {
      title: "类型",
      dataIndex: "strategy_type",
      key: "strategy_type",
      render: (type: string) => (
        <Tag color={strategyTypeColors[type]}>
          {strategyTypeOptions.find((o) => o.value === type)?.label ?? type}
        </Tag>
      ),
    },
    {
      title: "描述",
      dataIndex: "description",
      key: "description",
      ellipsis: true,
    },
    {
      title: "参数",
      dataIndex: "params",
      key: "params",
      render: (params: Record<string, unknown>) => (
        <Space size={[0, 4]} wrap>
          {Object.entries(params).slice(0, 3).map(([k, v]) => (
            <Tag key={k} style={{ fontSize: 11 }}>
              {k}={typeof v === "object" ? "…" : String(v)}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: "操作",
      key: "action",
      render: (_, record) => (
        <Space>
          <Button
            type="primary"
            size="small"
            icon={<RocketOutlined />}
            onClick={() => handleRunBacktest(record)}
          >
            运行回测
          </Button>
        </Space>
      ),
    },
  ];

  const backtestColumns: ColumnsType<BacktestResult> = [
    {
      title: "策略ID",
      dataIndex: "strategy_id",
      key: "strategy_id",
      width: 150,
    },
    {
      title: "年化收益",
      dataIndex: "annualized_return",
      key: "annualized_return",
      render: (v: number) => (
        <Text style={{ color: (v ?? 0) >= 0 ? "#3f8600" : "#cf1322" }}>
          {(v ?? 0).toFixed(2)}%
        </Text>
      ),
      sorter: (a, b) => (a.annualized_return ?? 0) - (b.annualized_return ?? 0),
    },
    {
      title: "夏普比",
      dataIndex: "sharpe_ratio",
      key: "sharpe_ratio",
      render: (v: number) => (v ?? 0).toFixed(2),
      sorter: (a, b) => (a.sharpe_ratio ?? 0) - (b.sharpe_ratio ?? 0),
    },
    {
      title: "最大回撤",
      dataIndex: "max_drawdown",
      key: "max_drawdown",
      render: (v: number) => (
        <Text style={{ color: "#cf1322" }}>{(v ?? 0).toFixed(2)}%</Text>
      ),
    },
    {
      title: "操作",
      key: "action",
      render: (_, record) => (
        <Button
          size="small"
          icon={<EyeOutlined />}
          onClick={() => navigate(`/backtest/${record.id}`)}
        >
          详情
        </Button>
      ),
    },
  ];

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 24,
        }}
      >
        <Title level={2} style={{ margin: 0 }}>
          策略列表
        </Title>
        <Space>
          <Select
            value={typeFilter}
            onChange={setTypeFilter}
            options={strategyTypeOptions}
            style={{ width: 150 }}
            placeholder="筛选类型"
          />
          <Button icon={<ReloadOutlined />} onClick={fetchData}>
            刷新
          </Button>
        </Space>
      </div>

      {/* Strategy Table */}
      <Table
        columns={strategyColumns}
        dataSource={filteredStrategies}
        rowKey="id"
        loading={loading}
        pagination={false}
        style={{ marginBottom: 32 }}
      />

      {/* Backtest History */}
      <Title level={4} style={{ marginBottom: 16 }}>
        回测历史
      </Title>
      <Table
        columns={backtestColumns}
        dataSource={backtests}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 10 }}
      />

      {/* Run Backtest Modal */}
      <Modal
        title={`运行回测 — ${selectedStrategy?.name ?? ""}`}
        open={modalOpen}
        onOk={handleSubmitBacktest}
        onCancel={() => setModalOpen(false)}
        confirmLoading={running}
        okText="开始回测"
        cancelText="取消"
        width={600}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="开始日期"
                name="start_date"
                rules={[{ required: true, message: "请输入开始日期" }]}
              >
                <Input placeholder="2024-01-01" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="结束日期"
                name="end_date"
                rules={[{ required: true, message: "请输入结束日期" }]}
              >
                <Input placeholder="2025-12-31" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item label="股票代码（可选）" name="symbols">
            <Input placeholder="多个用逗号分隔，如 000001,600519" />
          </Form.Item>

          {selectedStrategy && (
            <>
              <Title level={5} style={{ marginBottom: 8 }}>
                策略参数
              </Title>
              {Object.entries(selectedStrategy.params).map(([key, defaultVal]) => (
                <Form.Item key={key} label={key} name={key}>
                  {typeof defaultVal === "number" ? (
                    <InputNumber style={{ width: "100%" }} />
                  ) : Array.isArray(defaultVal) ? (
                    <Input placeholder={JSON.stringify(defaultVal)} />
                  ) : (
                    <Input />
                  )}
                </Form.Item>
              ))}
            </>
          )}
        </Form>
      </Modal>
    </div>
  );
}
