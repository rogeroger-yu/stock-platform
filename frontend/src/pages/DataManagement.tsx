import { useEffect, useState } from "react";
import {
  Typography,
  Card,
  Table,
  Button,
  Space,
  Tag,
  Statistic,
  Row,
  Col,
  Empty,
  message,
  Progress,
} from "antd";
import {
  DatabaseOutlined,
  ReloadOutlined,
  CloudDownloadOutlined,
  CheckCircleOutlined,
} from "@ant-design/icons";
import { api } from "../api/client";
import type { ColumnsType } from "antd/es/table";

const { Title, Text, Paragraph } = Typography;

interface StockData {
  symbol: string;
  start?: string;
  end?: string;
  rows?: number;
  missing_pct?: number;
  error?: string;
}

export default function DataManagement() {
  const [stocks, setStocks] = useState<StockData[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchStocks = async () => {
    setLoading(true);
    try {
      const data = await api.getAvailableStocks();
      setStocks(data);
    } catch {
      message.error("获取数据列表失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStocks();
  }, []);

  const totalRows = stocks.reduce((sum, s) => sum + (s.rows || 0), 0);
  const avgMissing =
    stocks.length > 0
      ? stocks.reduce((sum, s) => sum + (s.missing_pct || 0), 0) / stocks.length
      : 0;

  const columns: ColumnsType<StockData> = [
    {
      title: "股票代码",
      dataIndex: "symbol",
      key: "symbol",
      render: (v: string) => <Text strong>{v}</Text>,
    },
    {
      title: "数据起始",
      dataIndex: "start",
      key: "start",
      render: (v: string) => v || "-",
    },
    {
      title: "数据截止",
      dataIndex: "end",
      key: "end",
      render: (v: string) => v || "-",
    },
    {
      title: "数据条数",
      dataIndex: "rows",
      key: "rows",
      render: (v: number) => (v ? v.toLocaleString() : "-"),
    },
    {
      title: "缺失率",
      dataIndex: "missing_pct",
      key: "missing_pct",
      render: (v: number | undefined) => {
        if (v == null) return "-";
        const color = v < 1 ? "#3f8600" : v < 5 ? "#faad14" : "#cf1322";
        return (
          <Space>
            <Progress
              percent={Math.min(100 - v, 100)}
              size="small"
              strokeColor={color}
              style={{ width: 80 }}
              showInfo={false}
            />
            <Text style={{ color, fontSize: 12 }}>{v.toFixed(1)}%</Text>
          </Space>
        );
      },
    },
    {
      title: "状态",
      key: "status",
      render: (_: unknown, record: StockData) =>
        record.error ? (
          <Tag color="error">{record.error}</Tag>
        ) : (
          <Tag icon={<CheckCircleOutlined />} color="success">
            正常
          </Tag>
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
        <div>
          <Title level={2} style={{ margin: 0 }}>
            📊 数据管理
          </Title>
          <Paragraph type="secondary" style={{ margin: "4px 0 0" }}>
            查看本地股票数据覆盖情况
          </Paragraph>
        </div>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={fetchStocks}
            loading={loading}
          >
            刷新
          </Button>
        </Space>
      </div>

      {/* Stats */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="已下载股票"
              value={stocks.length}
              suffix="只"
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="总数据条数"
              value={totalRows}
              prefix={<CloudDownloadOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="平均缺失率"
              value={avgMissing.toFixed(2)}
              suffix="%"
              valueStyle={{ color: avgMissing < 1 ? "#3f8600" : "#faad14" }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="数据源"
              value="akshare"
              prefix={<CloudDownloadOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Table */}
      {stocks.length === 0 ? (
        <Card>
          <Empty description="暂无本地数据，需要在服务器端下载股票数据">
            <Text type="secondary">
              使用 <Text code>python download_sina.py</Text> 或 API 下载数据
            </Text>
          </Empty>
        </Card>
      ) : (
        <Card>
          <Table
            columns={columns}
            dataSource={stocks}
            rowKey="symbol"
            loading={loading}
            pagination={{ pageSize: 20 }}
            size="middle"
          />
        </Card>
      )}
    </div>
  );
}
