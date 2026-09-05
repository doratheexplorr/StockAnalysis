import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Watchlist from "./pages/Watchlist";
import StockDetail from "./pages/StockDetail";
import SignalDetail from "./pages/SignalDetail";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="watchlist" element={<Watchlist />} />
        <Route path="stocks/:symbol" element={<StockDetail />} />
        <Route path="signals/:id" element={<SignalDetail />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
