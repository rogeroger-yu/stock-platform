import { useEffect, useState } from "react";
import {
  Typography,
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Button,
  Space,
  Tag,
  Empty,
  message,
  Descriptions,
  Divider,
} from "antd";
import {
  WalletOutlined,
  ReloadOutlined,
  PlayCircleOutlined,
  FundOutlined,
} from "@ant-design/icons";
import { api } from "../api/client";
import type { ColumnsType } from "antd/es/table";

const { Title, Paragraph, Text } = Typography;

interface AccountInfo {
  account_id: string;
  cash: number;
  total_value: number;
  total_pnl: number;
  positions: Record<
    string,
    {
      quantity: number;
      avg_cost: number;
      current_price: number;
      market_value: number;
      unrealized_pnl: number;
    }
  >;
}

interface Order {
  order_id: string;
  symbol: string;
  side: string;
  quantity: number;
  price: number;
  filled_price: number;
  status: string;
  commission: number;
  created_at: string;
}

export default function PaperTrade() {
  const [account, setAccount] = useState<AccountInfo | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(false);
  const [dailyChecking, setDailyChecking] = useState(false);

  const fetchAccount = async () => {
    setLoading(true);
    try {
      const data = await api.getPaperAccount();
      setAccount(data as AccountInfo);
    } catch {
      message.error("获取账户信息失败");
    } finally {
      setLoading(false);
    }
  };

  const fetchOrders = async () => {
    try {
      // Use the trades endpoint as a proxy for order history
      const data = await api.getSignalHistory(50);
      setOrders(data as Order[]);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    fetchAccount();
    fetchOrders();
  }, []);

  const handleDailyCheck = async () => {
    setDailyChecking(true);
    try {
      const result = await api.dailyCheck(false);
      message.success(
        `每日检查完成，${(result as { signals?: unknown[] }).signals?.length || 0} 个信号`
      );
      fetchAccount();
    } catch {
      message.error("每日检查失败");
    } finally {
      setDailyChecking(false);
    }
  };

  const handleReset = async () => {
    try {
      await fetch(`${import.meta.env.VITE_API_BASE || "http://47.97.26.218:8000"}/api/paper/reset`, {
        method: "POST",
      });
      message.success("账户已重置");
      fetchAccount();
    } catch {
      message.error("重置失败");
    }
  };

  const positionColumns: ColumnsType<
    AccountInfo["positions"][string] & { symbol: string }
  > = [
    {
      title: "股票代码",
      dataIndex: "symbol",
      key: "symbol",
      render: (v: string) => <Text strong>{v}</Text>,
    },
    {
      title: "持仓数量",
      dataIndex: "quantity",
      key: "quantity",
    },
    {
      title: "成本价",
      dataIndex: "avg_cost",
      key: "avg_cost",
      render: (v: number) => `¥${v.toFixed(2)}`,
    },
    {
      title: "当前价",
      dataIndex: "current_price",
      key: "current_price",
      render: (v: number) => `¥${v.toFixed(2)}`,
    },
    {
      title: "市值",
      dataIndex: "market_value",
      key: "market_value",
      render: (v: number) => `¥${v.toLocaleString()}`,
    },
    {
      title: "浮动盈亏",
      dataIndex: "unrealized_pnl",
      key: "unrealized_pnl",
      render: (v: number) => (
        <Text style={{ color: v >= 0 ? "#3f8600" : "#cf1322" }}>
          {v >= 0 ? "+" : ""}¥{v.toFixed(2)}
        </Text>
      ),
    },
  ];

  const positions = account
    ? Object.entries(account.positions).map(([sym, pos]) => ({
        symbol: sym,
        ...pos,
      }))
    : [];

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
        <div>
          <Title level={2} style={{ margin: 0 }}>
            💰 模拟交易
          </Title>
          <Paragraph type="secondary" style={{ margin: "4px 0 0" }}>
            Paper Trading — 不接真账户，纯模拟
          </Paragraph>
        </div>
        <Space>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={handleDailyCheck}
            loading={dailyChecking}
          >
            每日信号检查
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchAccount} loading={loading}>
            刷新
          </Button>
          <Button danger onClick={handleReset}>
            重置账户
          </Button>
        </Space>
      </div>

      {/* Account Overview */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="可用资金"
              value={account?.cash ?? 0}
              precision={0}
              prefix="¥"
              suffix={<WalletOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="账户总值"
              value={account?.total_value ?? 0}
              precision={0}
              prefix="¥"
              prefixStyle={{ color: "#1677ff" }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="总盈亏"
              value={account?.total_pnl ?? 0}
              precision={0}
              prefix="¥"
              valueStyle={{
                color: (account?.total_pnl ?? 0) >= 0 ? "#3f8600" : "#cf1322",
              }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="持仓数量"
              value={positions.length}
              suffix="只"
              prefix={<FundOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Positions */}
      <Card
        title="当前持仓"
        style={{ marginBottom: 24 }}
        extra={<Button size="small" icon={<ReloadOutlined />} onClick={fetchAccount} />}
      >
        {positions.length > 0 ? (
          <Table
            columns={positionColumns}
            dataSource={positions}
            rowKey="symbol"
            pagination={false}
            size="small"
          />
        ) : (
          <Empty description="暂无持仓" />
        )}
      </Card>

      {/* Recent Activity */}
      <Card title="最近交易记录">
        {orders.length > 0 ? (
          <Table
            columns={[
              { title: "订单ID", dataIndex: "order_id", key: "id", width: 100 },
              { title: "股票", dataIndex: "symbol", key: "symbol" },
              {
                title: "方向",
                dataIndex: "side",
                key: "side",
                render: (v: string) => (
                  <Tag color={v === "buy" ? "green" : "red"}>
                    {v === "buy" ? "买入" : "卖出"}
                  </Tag>
                ),
              },
              { title: "数量", dataIndex: "quantity", key: "qty" },
              {
                title: "价格",
                dataIndex: "price",
                key: "price",
                render: (v: number) => `¥${v?.toFixed(2) ?? "-"}`,
              },
              {
                title: "状态",
                dataIndex: "status",
                key: "status",
                render: (v: string) => (
                  <Tag color={v === "filled" ? "success" : "default"}>
                    {v === "filled" ? "已成交" : v}
                  </Tag>
                ),
              },
            ]}
            dataSource={orders}
            rowKey="order_id"
            pagination={{ pageSize: 10 }}
            size="small"
          />
        ) : (
          <Empty description="暂无交易记录" />
        )}
      </Card>
    </div>
  );
}
