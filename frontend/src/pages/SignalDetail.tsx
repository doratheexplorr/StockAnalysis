import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { SignalDetail as SignalDetailType } from "../types";
import { ClassificationBadge, DirectionBadge } from "../components/Badge";

export default function SignalDetail() {
  const { id } = useParams<{ id: string }>();
  const [signal, setSignal] = useState<SignalDetailType | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api
      .get<SignalDetailType>(`/api/signals/${id}`)
      .then(setSignal)
      .catch((e) => setError(String(e)));
  }, [id]);

  if (error) return <div className="text-red-400">{error}</div>;
  if (!signal) return <div className="text-slate-500">Loading…</div>;

  const breakdown = Object.entries(signal.score_breakdown).filter(([k]) => k !== "weights_used" && k !== "news_conflict_penalty_factor");

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <Link to={`/stocks/${signal.symbol}`} className="text-2xl font-bold hover:underline">
            {signal.symbol}
          </Link>
          <span className="text-slate-500 ml-2">{signal.timeframe}</span>
        </div>
        <div className="flex items-center gap-2">
          <DirectionBadge direction={signal.direction} />
          <ClassificationBadge classification={signal.classification} score={signal.quality_score} />
        </div>
      </div>

      <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
        <div className="text-sm text-slate-400 mb-1">Pattern</div>
        <div className="text-lg font-semibold">{signal.pattern_name}</div>
        <p className="text-sm text-slate-400 mt-2">{signal.explanation}</p>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-4 space-y-2">
          <h3 className="font-semibold text-sm text-slate-400">Entry / Risk</h3>
          <Row label="Current price" value={`$${signal.current_price.toFixed(2)}`} />
          <Row label="Entry" value={`$${signal.entry_price.toFixed(2)}`} />
          <Row label="Stop loss" value={`$${signal.stop_loss.toFixed(2)}`} />
          <Row label="Target 1" value={`$${signal.target_1.toFixed(2)} (1:${signal.rr_t1.toFixed(1)})`} />
          <Row label="Target 2" value={`$${signal.target_2.toFixed(2)} (1:${signal.rr_t2.toFixed(1)})`} />
          <Row label="Target 3" value={`$${signal.target_3.toFixed(2)} (1:${signal.rr_t3.toFixed(1)})`} />
          <Row label="Risk / share" value={`$${signal.risk_per_share.toFixed(2)}`} />
          <p className="text-xs text-slate-500 pt-2 border-t border-slate-800 mt-2">{signal.risk_methodology}</p>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-900 p-4 space-y-2">
          <h3 className="font-semibold text-sm text-slate-400">Score breakdown</h3>
          {breakdown.map(([key, value]) => (
            <Row key={key} label={key.replace(/_/g, " ")} value={String(value)} />
          ))}
          <div className="pt-2 border-t border-slate-800 mt-2 font-semibold">Total: {signal.quality_score.toFixed(1)}/100</div>
        </div>
      </div>

      <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
        <h3 className="font-semibold text-sm text-slate-400 mb-2">Technical confirmations</h3>
        <ul className="space-y-1 text-sm">
          {signal.technical_confirmations.map((c, i) => (
            <li key={i} className={c.passed ? "text-emerald-400" : "text-slate-600"}>
              {c.passed ? "✓" : "✗"} {c.detail || c.label}
            </li>
          ))}
        </ul>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
          <h3 className="font-semibold text-sm text-slate-400 mb-2">News context</h3>
          <div className="text-sm mb-1">
            {signal.news_context.status === "supportive" && "🟢 Supportive"}
            {signal.news_context.status === "conflicting" && "🔴 Conflicting"}
            {signal.news_context.status === "neutral" && "⚪ Neutral"}
            {signal.news_context.status === "unavailable" && "⚪ Unavailable"}
          </div>
          <p className="text-xs text-slate-500">{signal.news_context.reason}</p>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
          <h3 className="font-semibold text-sm text-slate-400 mb-2">Market context</h3>
          <Row label="Regime" value={signal.market_context.regime} />
          <Row label="S&P 500 trend" value={signal.market_context.spy_trend} />
          <Row label="Sector" value={signal.market_context.sector} />
          <Row label="Sector trend" value={signal.market_context.sector_trend} />
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-slate-500 capitalize">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
