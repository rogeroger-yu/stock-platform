import { useState } from "react";
import { Layout as AntLayout, Menu, Typography, theme } from "antd";
import {
  HomeOutlined,
  LineChartOutlined,
  SwapOutlined,
  DatabaseOutlined,
  ThunderboltOutlined,
  WalletOutlined,
} from "@ant-design/icons";
import { Outlet, useNavigate, useLocation } from "react-router-dom";

const { Header, Sider, Content, Footer } = AntLayout;
const { Text } = Typography;

const navItems = [
  { key: "/", icon: <HomeOutlined />, label: "首页" },
  { key: "/strategies", icon: <LineChartOutlined />, label: "策略列表" },
  { key: "/batch", icon: <ThunderboltOutlined />, label: "批量排名" },
  { key: "/compare", icon: <SwapOutlined />, label: "策略对比" },
  { key: "/paper", icon: <WalletOutlined />, label: "模拟交易" },
  { key: "/data", icon: <DatabaseOutlined />, label: "数据管理" },
];

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();

  // Determine active menu key
  const activeKey = navItems.find((item) =>
    item.key === "/" ? location.pathname === "/" : location.pathname.startsWith(item.key)
  )?.key ?? "/";

  return (
    <AntLayout style={{ minHeight: "100vh" }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        style={{ background: "#001529" }}
      >
        <div
          style={{
            height: 64,
            display: "flex",
            alignItems: "center",
            justifyContent: collapsed ? "center" : "flex-start",
            padding: collapsed ? 0 : "0 16px",
            borderBottom: "1px solid rgba(255,255,255,0.1)",
          }}
        >
          <Text
            style={{
              color: "#fff",
              fontWeight: 700,
              fontSize: collapsed ? 16 : 16,
              whiteSpace: "nowrap",
            }}
          >
            {collapsed ? "📈" : "📈 策略研发平台"}
          </Text>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[activeKey]}
          items={navItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <AntLayout>
        <Header
          style={{
            padding: "0 24px",
            background: colorBgContainer,
            display: "flex",
            alignItems: "center",
            borderBottom: "1px solid #f0f0f0",
            boxShadow: "0 1px 4px rgba(0,0,0,0.05)",
          }}
        >
          <Text strong style={{ fontSize: 18 }}>
            股票策略研发平台
          </Text>
          <Text type="secondary" style={{ marginLeft: 12, fontSize: 13 }}>
            v0.1.0
          </Text>
        </Header>
        <Content
          style={{
            margin: 24,
            padding: 24,
            background: colorBgContainer,
            borderRadius: borderRadiusLG,
            minHeight: 280,
          }}
        >
          <Outlet />
        </Content>
        <Footer style={{ textAlign: "center", color: "#999" }}>
          Stock Strategy Platform ©2026 · 基于 akshare 数据源
        </Footer>
      </AntLayout>
    </AntLayout>
  );
}
