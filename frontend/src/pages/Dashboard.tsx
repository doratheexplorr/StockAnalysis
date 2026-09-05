import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { SignalListItem, SystemStatus, WatchlistItem } from "../types";
import SignalCard from "../components/SignalCard";

export default function Dashboard() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [strongest, setStrongest] = useState<SignalListItem[]>([]);
  const [recent, setRecent] = useState<SignalListItem[]>([]);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.get<SystemStatus>("/api/status"),
      api.get<SignalListItem[]>("/api/signals/strongest?limit=6"),
      api.get<SignalListItem[]>("/api/signals?limit=10"),
      api.get<WatchlistItem[]>("/api/watchlist"),
    ])
      .then(([s, strongestSignals, recentSignals, wl]) => {
        setStatus(s);
        setStrongest(strongestSignals);
        setRecent(recentSignals);
        setWatchlist(wl);
      })
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <div className="text-red-400">Failed to load dashboard: {error}</div>;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="Market" value={status?.market_status ?? "…"} />
        <StatCard label="Watchlist" value={String(watchlist.filter((w) => w.enabled).length)} />
        <StatCard label="Data provider" value={status?.market_data_provider ?? "…"} />
        <StatCard label="Polling" value={status?.polling_enabled ? "enabled" : "disabled"} />
      </div>

      <section>
        <h2 className="text-lg font-semibold mb-2">Strongest active setups</h2>
        {strongest.length === 0 ? (
          <EmptyState text="No qualifying setups yet. Once the scheduler finds a high-quality signal it will appear here." />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {strongest.map((s) => (
              <SignalCard key={s.id} signal={s} />
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-2">Recent signals</h2>
        {recent.length === 0 ? (
          <EmptyState text="No signals recorded yet." />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {recent.map((s) => (
              <SignalCard key={s.id} signal={s} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-3">
      <div className="text-xs text-slate-500 uppercase tracking-wide">{label}</div>
      <div className="text-lg font-semibold mt-0.5 capitalize">{value}</div>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return <div className="text-sm text-slate-500 border border-dashed border-slate-800 rounded-lg p-6 text-center">{text}</div>;
}
