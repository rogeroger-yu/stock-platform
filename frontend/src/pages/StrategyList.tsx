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
  Popconfirm,
  Tooltip,
} from "antd";
import {
  RocketOutlined,
  ReloadOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ExperimentOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { api, type Strategy, type StrategyCreate } from "../api/client";
import type { ColumnsType } from "antd/es/table";

const { Title, Text } = Typography;

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
};

export default function StrategyList() {
  const navigate = useNavigate();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(false);
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [backtestModalOpen, setBacktestModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [running, setRunning] = useState(false);
  const [backtestForm] = Form.useForm();
  const [editForm] = Form.useForm();
  const [createForm] = Form.useForm();

  const fetchStrategies = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getStrategies(typeFilter || undefined);
      setStrategies(data);
    } finally {
      setLoading(false);
    }
  }, [typeFilter]);

  useEffect(() => {
    fetchStrategies();
  }, [fetchStrategies]);

  const handleRunBacktest = (strategy: Strategy) => {
    setSelectedStrategy(strategy);
    backtestForm.setFieldsValue({
      symbols: "000001",
      start_date: "2020-01-01",
      end_date: "2025-05-01",
    });
    setBacktestModalOpen(true);
  };

  const handleSubmitBacktest = async () => {
    if (!selectedStrategy) return;
    try {
      const values = await backtestForm.validateFields();
      setRunning(true);
      const symbols = (values.symbols as string)
        .split(",")
        .map((s: string) => s.trim())
        .filter(Boolean);

      const result = await api.runBacktest({
        strategy_id: selectedStrategy.id,
        symbols,
        start_date: values.start_date,
        end_date: values.end_date,
        initial_capital: values.initial_capital || 1_000_000,
      });
      message.success(`回测完成！年化收益: ${(result.annualized_return * 100).toFixed(2)}%`);
      setBacktestModalOpen(false);
      fetchStrategies();
      navigate(`/backtest/${result.id}`);
    } catch (err) {
      if (err !== false) message.error("回测失败，请检查参数");
    } finally {
      setRunning(false);
    }
  };

  const handleEdit = (strategy: Strategy) => {
    setSelectedStrategy(strategy);
    editForm.setFieldsValue({
      name: strategy.name,
      description: strategy.description,
      params: JSON.stringify(strategy.params, null, 2),
    });
    setEditModalOpen(true);
  };

  const handleUpdate = async () => {
    if (!selectedStrategy) return;
    try {
      const values = await editForm.validateFields();
      let params = {};
      try {
        params = JSON.parse(values.params);
      } catch {
        message.error("参数格式错误，请输入合法 JSON");
        return;
      }
      await api.updateStrategy(selectedStrategy.id, {
        name: values.name,
        description: values.description,
        params,
      });
      message.success("策略已更新");
      setEditModalOpen(false);
      fetchStrategies();
    } catch (err) {
      if (err !== false) message.error("更新失败");
    }
  };

  const handleDelete = async (id: number) => {
    await api.deleteStrategy(id);
    message.success("已删除");
    fetchStrategies();
  };

  const handleCreate = async () => {
    try {
      const values = await createForm.validateFields();
      let params = {};
      if (values.params) {
        try {
          params = JSON.parse(values.params);
        } catch {
          message.error("参数格式错误，请输入合法 JSON");
          return;
        }
      }
      const req: StrategyCreate = {
        name: values.name,
        strategy_type: values.strategy_type,
        description: values.description || "",
        params,
      };
      await api.createStrategy(req);
      message.success("策略已创建");
      setCreateModalOpen(false);
      createForm.resetFields();
      fetchStrategies();
    } catch (err) {
      if (err !== false) message.error("创建失败");
    }
  };

  const handleSeedDefaults = async () => {
    try {
      const result = await api.seedDefaults();
      message.success(`已初始化 ${result.created.length} 个默认策略`);
      fetchStrategies();
    } catch {
      message.error("初始化失败");
    }
  };

  const columns: ColumnsType<Strategy> = [
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
        <Tag color={strategyTypeColors[type] || "default"}>
          {type}
        </Tag>
      ),
    },
    {
      title: "描述",
      dataIndex: "description",
      key: "description",
      ellipsis: true,
      width: 200,
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
      title: "回测次数",
      dataIndex: "backtest_count",
      key: "backtest_count",
      width: 80,
      render: (v: number) => v || 0,
    },
    {
      title: "最近年化",
      dataIndex: "last_annual_return",
      key: "last_annual_return",
      width: 90,
      render: (v: number | null) =>
        v != null ? (
          <Text style={{ color: v >= 0 ? "#3f8600" : "#cf1322" }}>
            {(v * 100).toFixed(1)}%
          </Text>
        ) : (
          <Text type="secondary">-</Text>
        ),
    },
    {
      title: "操作",
      key: "action",
      width: 280,
      render: (_, record) => (
        <Space>
          <Tooltip title="运行回测">
            <Button
              type="primary"
              size="small"
              icon={<RocketOutlined />}
              onClick={() => handleRunBacktest(record)}
            >
              回测
            </Button>
          </Tooltip>
          <Tooltip title="编辑参数">
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Popconfirm
            title="确定删除此策略？"
            onConfirm={() => handleDelete(record.id)}
          >
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
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
          策略管理
        </Title>
        <Space>
          <Select
            value={typeFilter}
            onChange={setTypeFilter}
            style={{ width: 160 }}
            placeholder="筛选类型"
            allowClear
            options={[
              { label: "全部类型", value: "" },
              ...Object.entries(strategyTypeColors).map(([k]) => ({
                label: k,
                value: k,
              })),
            ]}
          />
          <Button icon={<PlusOutlined />} type="primary" onClick={() => setCreateModalOpen(true)}>
            新建策略
          </Button>
          <Button icon={<ExperimentOutlined />} onClick={handleSeedDefaults}>
            初始化默认策略
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchStrategies}>
            刷新
          </Button>
        </Space>
      </div>

      <Table
        columns={columns}
        dataSource={strategies}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 20 }}
      />

      {/* Run Backtest Modal */}
      <Modal
        title={`运行回测 — ${selectedStrategy?.name ?? ""}`}
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
              <Form.Item label="开始日期" name="start_date" rules={[{ required: true }]}>
                <Input placeholder="2020-01-01" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="结束日期" name="end_date" rules={[{ required: true }]}>
                <Input placeholder="2025-05-01" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="初始资金" name="initial_capital">
            <InputNumber style={{ width: "100%" }} min={10000} step={100000} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Create Strategy Modal */}
      <Modal
        title="新建策略"
        open={createModalOpen}
        onOk={handleCreate}
        onCancel={() => setCreateModalOpen(false)}
        okText="创建"
        cancelText="取消"
        width={600}
      >
        <Form form={createForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item label="策略名称" name="name" rules={[{ required: true }]}>
            <Input placeholder="我的策略" />
          </Form.Item>
          <Form.Item label="策略类型" name="strategy_type" rules={[{ required: true }]}>
            <Select
              placeholder="选择策略类型"
              options={Object.entries(strategyTypeColors).map(([k]) => ({
                label: k,
                value: k,
              }))}
            />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item label="参数（JSON）" name="params">
            <Input.TextArea
              rows={4}
              placeholder='{"ma_window": 20, "min_holding": 10}'
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* Edit Strategy Modal */}
      <Modal
        title={`编辑策略 — ${selectedStrategy?.name ?? ""}`}
        open={editModalOpen}
        onOk={handleUpdate}
        onCancel={() => setEditModalOpen(false)}
        okText="保存"
        cancelText="取消"
        width={600}
      >
        <Form form={editForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item label="策略名称" name="name">
            <Input />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item label="参数（JSON）" name="params">
            <Input.TextArea rows={6} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
