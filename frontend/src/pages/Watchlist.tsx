import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { PatternInfo, WatchlistItem } from "../types";

const ALL_TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"];
const ALL_CHANNELS = ["in_app", "email", "telegram"];

export default function Watchlist() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [patterns, setPatterns] = useState<PatternInfo[]>([]);
  const [newSymbol, setNewSymbol] = useState("");
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    api.get<WatchlistItem[]>("/api/watchlist").then(setItems).catch((e) => setError(String(e)));
  }

  useEffect(() => {
    refresh();
    api.get<PatternInfo[]>("/api/settings/patterns").then(setPatterns);
  }, []);

  async function addSymbol() {
    if (!newSymbol.trim()) return;
    setError(null);
    try {
      await api.post("/api/watchlist", { symbol: newSymbol.trim().toUpperCase() });
      setNewSymbol("");
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function update(item: WatchlistItem, patch: Partial<WatchlistItem>) {
    await api.patch(`/api/watchlist/${item.id}`, patch);
    refresh();
  }

  async function remove(item: WatchlistItem) {
    await api.delete(`/api/watchlist/${item.id}`);
    refresh();
  }

  function toggleTimeframe(item: WatchlistItem, tf: string) {
    const current = item.timeframes ?? [];
    const next = current.includes(tf) ? current.filter((t) => t !== tf) : [...current, tf];
    update(item, { timeframes: next.length ? next : null } as any);
  }

  function toggleChannel(item: WatchlistItem, channel: string) {
    const current = item.notification_channels ?? ["in_app"];
    const next = current.includes(channel) ? current.filter((c) => c !== channel) : [...current, channel];
    update(item, { notification_channels: next.length ? next : null } as any);
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Watchlist</h1>

      <div className="flex gap-2">
        <input
          value={newSymbol}
          onChange={(e) => setNewSymbol(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && addSymbol()}
          placeholder="Add ticker, e.g. NVDA"
          className="bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm w-48"
        />
        <button onClick={addSymbol} className="bg-sky-600 hover:bg-sky-500 rounded-md px-4 py-2 text-sm font-medium">
          Add
        </button>
      </div>
      {error && <div className="text-red-400 text-sm">{error}</div>}

      <div className="space-y-3">
        {items.map((item) => (
          <div key={item.id} className="rounded-lg border border-slate-800 bg-slate-900 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <Link to={`/stocks/${item.symbol}`} className="font-semibold text-lg hover:underline">
                {item.symbol}
              </Link>
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-1.5 text-sm text-slate-400">
                  <input type="checkbox" checked={item.enabled} onChange={(e) => update(item, { enabled: e.target.checked })} />
                  Monitoring
                </label>
                <button onClick={() => remove(item)} className="text-xs text-red-400 hover:text-red-300">
                  Remove
                </button>
              </div>
            </div>

            <div>
              <div className="text-xs text-slate-500 mb-1">Timeframes</div>
              <div className="flex flex-wrap gap-1.5">
                {ALL_TIMEFRAMES.map((tf) => (
                  <button
                    key={tf}
                    onClick={() => toggleTimeframe(item, tf)}
                    className={`px-2 py-1 rounded text-xs border ${
                      (item.timeframes ?? []).includes(tf)
                        ? "bg-sky-600 border-sky-500"
                        : "bg-slate-800 border-slate-700 text-slate-400"
                    }`}
                  >
                    {tf}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <div className="text-xs text-slate-500 mb-1">Notification channels</div>
              <div className="flex flex-wrap gap-1.5">
                {ALL_CHANNELS.map((c) => (
                  <button
                    key={c}
                    onClick={() => toggleChannel(item, c)}
                    className={`px-2 py-1 rounded text-xs border ${
                      (item.notification_channels ?? ["in_app"]).includes(c)
                        ? "bg-emerald-600 border-emerald-500"
                        : "bg-slate-800 border-slate-700 text-slate-400"
                    }`}
                  >
                    {c}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-xs text-slate-500">Min score override</label>
              <input
                type="number"
                min={0}
                max={100}
                placeholder="global default"
                value={item.min_score_override ?? ""}
                onChange={(e) => update(item, { min_score_override: e.target.value ? Number(e.target.value) : null } as any)}
                className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs w-32"
              />
            </div>

            <details>
              <summary className="text-xs text-slate-500 cursor-pointer">Enabled patterns ({(item.enabled_patterns ?? patterns.map((p) => p.key)).length} of {patterns.length})</summary>
              <div className="flex flex-wrap gap-1.5 mt-2">
                {patterns.map((p) => {
                  const enabledList = item.enabled_patterns ?? patterns.map((pp) => pp.key);
                  const active = enabledList.includes(p.key);
                  return (
                    <button
                      key={p.key}
                      onClick={() => {
                        const next = active ? enabledList.filter((k) => k !== p.key) : [...enabledList, p.key];
                        update(item, { enabled_patterns: next } as any);
                      }}
                      className={`px-2 py-1 rounded text-xs border ${
                        active ? "bg-indigo-600 border-indigo-500" : "bg-slate-800 border-slate-700 text-slate-500"
                      }`}
                    >
                      {p.display_name}
                    </button>
                  );
                })}
              </div>
            </details>
          </div>
        ))}
        {items.length === 0 && (
          <div className="text-sm text-slate-500 border border-dashed border-slate-800 rounded-lg p-6 text-center">
            Your watchlist is empty. Add a ticker above to start monitoring it.
          </div>
        )}
      </div>
    </div>
  );
}
