import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import StrategyList from "./pages/StrategyList";
import BacktestDetail from "./pages/BacktestDetail";
import Compare from "./pages/Compare";

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/strategies" element={<StrategyList />} />
        <Route path="/backtest/:id" element={<BacktestDetail />} />
        <Route path="/compare" element={<Compare />} />
      </Route>
    </Routes>
  );
}

export default App;
