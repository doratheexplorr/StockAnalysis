import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { createChart, ColorType, type IChartApi } from "lightweight-charts";
import { api } from "../api/client";
import type { SignalListItem } from "../types";
import SignalCard from "../components/SignalCard";

const TIMEFRAMES = ["15m", "1h", "4h", "1d"];

interface Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export default function StockDetail() {
  const { symbol } = useParams<{ symbol: string }>();
  const [timeframe, setTimeframe] = useState("1d");
  const [signals, setSignals] = useState<SignalListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!symbol) return;
    api.get<SignalListItem[]>(`/api/signals?symbol=${symbol}&limit=25`).then(setSignals).catch(() => {});
  }, [symbol]);

  useEffect(() => {
    if (!symbol || !containerRef.current) return;
    setError(null);

    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const chart = createChart(containerRef.current, {
      layout: { background: { type: ColorType.Solid, color: "#0f172a" }, textColor: "#cbd5e1" },
      grid: { vertLines: { color: "#1e293b" }, horzLines: { color: "#1e293b" } },
      height: 420,
      autoSize: true,
    });
    chartRef.current = chart;

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#16a34a",
      downColor: "#dc2626",
      borderVisible: false,
      wickUpColor: "#16a34a",
      wickDownColor: "#dc2626",
    });
    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });
    chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });

    api
      .get<Candle[]>(`/api/market-data/${symbol}?timeframe=${timeframe}&lookback_bars=250`)
      .then((data) => {
        candleSeries.setData(data.map((d) => ({ time: d.time as any, open: d.open, high: d.high, low: d.low, close: d.close })));
        volumeSeries.setData(
          data.map((d) => ({ time: d.time as any, value: d.volume, color: d.close >= d.open ? "#16a34a55" : "#dc262655" }))
        );
        chart.timeScale().fitContent();
      })
      .catch((e) => setError(String(e)));

    return () => {
      chart.remove();
      chartRef.current = null;
    };
  }, [symbol, timeframe]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">{symbol}</h1>
        <div className="flex gap-1">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={`px-2 py-1 rounded text-xs border ${
                timeframe === tf ? "bg-sky-600 border-sky-500" : "bg-slate-800 border-slate-700 text-slate-400"
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="text-amber-400 text-sm border border-amber-700/50 bg-amber-900/20 rounded-md p-3">
          Could not load chart data: {error}. This is expected if the configured market-data provider can't reach
          its API from this environment (e.g. sandboxed/offline network) — see README "Known limitations".
        </div>
      )}

      <div ref={containerRef} className="rounded-lg border border-slate-800 overflow-hidden" />

      <section>
        <h2 className="text-lg font-semibold mb-2">Signal history</h2>
        {signals.length === 0 ? (
          <div className="text-sm text-slate-500">No signals recorded for {symbol} yet.</div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {signals.map((s) => (
              <SignalCard key={s.id} signal={s} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
