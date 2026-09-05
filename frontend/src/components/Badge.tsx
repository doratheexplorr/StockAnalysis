import type { Classification, Direction } from "../types";

const classificationStyles: Record<Classification, string> = {
  exceptional: "bg-fuchsia-500/20 text-fuchsia-300 border-fuchsia-500/40",
  strong: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40",
  good: "bg-sky-500/20 text-sky-300 border-sky-500/40",
  watch: "bg-amber-500/20 text-amber-300 border-amber-500/40",
  ignore: "bg-slate-500/20 text-slate-400 border-slate-500/40",
};

export function ClassificationBadge({ classification, score }: { classification: Classification; score: number }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${classificationStyles[classification]}`}>
      {score.toFixed(0)}/100 · {classification.toUpperCase()}
    </span>
  );
}

export function DirectionBadge({ direction }: { direction: Direction }) {
  const styles =
    direction === "bullish"
      ? "bg-bull/20 text-green-400 border-green-600/40"
      : direction === "bearish"
      ? "bg-bear/20 text-red-400 border-red-600/40"
      : "bg-slate-500/20 text-slate-300 border-slate-500/40";
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${styles}`}>
      {direction === "bullish" ? "▲ Bullish" : direction === "bearish" ? "▼ Bearish" : "● Neutral"}
    </span>
  );
}
