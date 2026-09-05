import { Link } from "react-router-dom";
import type { SignalListItem } from "../types";
import { ClassificationBadge, DirectionBadge } from "./Badge";

export default function SignalCard({ signal }: { signal: SignalListItem }) {
  return (
    <Link
      to={`/signals/${signal.id}`}
      className="block rounded-lg border border-slate-800 bg-slate-900 p-4 hover:border-slate-600 transition-colors"
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-lg">{signal.symbol}</span>
          <span className="text-xs text-slate-400">{signal.timeframe}</span>
        </div>
        <ClassificationBadge classification={signal.classification} score={signal.quality_score} />
      </div>
      <div className="mt-2 flex items-center justify-between">
        <div className="text-sm text-slate-300">{signal.pattern_name}</div>
        <DirectionBadge direction={signal.direction} />
      </div>
      <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
        <span>Entry ${signal.entry_price.toFixed(2)}</span>
        <span>{new Date(signal.detected_at).toLocaleString()}</span>
      </div>
      {signal.status === "suppressed" && (
        <div className="mt-2 text-xs text-amber-400">Suppressed — see detail for reason</div>
      )}
    </Link>
  );
}
