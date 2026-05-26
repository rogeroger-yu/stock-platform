import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import StrategyList from "./pages/StrategyList";
import StrategyDetail from "./pages/StrategyDetail";
import BacktestDetail from "./pages/BacktestDetail";
import Compare from "./pages/Compare";
import DataManagement from "./pages/DataManagement";
import BatchRun from "./pages/BatchRun";
import PaperTrade from "./pages/PaperTrade";

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/strategies" element={<StrategyList />} />
        <Route path="/strategies/:id" element={<StrategyDetail />} />
        <Route path="/backtest/:id" element={<BacktestDetail />} />
        <Route path="/compare" element={<Compare />} />
        <Route path="/batch" element={<BatchRun />} />
        <Route path="/paper" element={<PaperTrade />} />
        <Route path="/data" element={<DataManagement />} />
      </Route>
    </Routes>
  );
}

export default App;
