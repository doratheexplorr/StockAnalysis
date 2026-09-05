import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { NotificationPreference, ScoringConfig } from "../types";

export default function Settings() {
  const [config, setConfig] = useState<ScoringConfig | null>(null);
  const [prefs, setPrefs] = useState<NotificationPreference[]>([]);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.get<ScoringConfig>("/api/settings/scoring").then(setConfig);
    api.get<NotificationPreference[]>("/api/settings/notifications").then(setPrefs);
  }, []);

  async function save() {
    if (!config) return;
    const updated = await api.put<ScoringConfig>("/api/settings/scoring", config);
    setConfig(updated);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  async function togglePref(pref: NotificationPreference) {
    const updated = await api.put<NotificationPreference>(`/api/settings/notifications/${pref.channel}`, {
      enabled: !pref.enabled,
      config: pref.config,
    });
    setPrefs((prev) => prev.map((p) => (p.channel === pref.channel ? updated : p)));
  }

  if (!config) return <div className="text-slate-500">Loading…</div>;

  const weightTotal = Object.values(config.weights).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-xl font-bold">Settings</h1>

      <section className="rounded-lg border border-slate-800 bg-slate-900 p-4 space-y-3">
        <h2 className="font-semibold">Scoring weights</h2>
        <p className="text-xs text-slate-500">
          Must sum to 100 to keep scores on a 0-100 scale. Currently: <span className={weightTotal === 100 ? "text-emerald-400" : "text-amber-400"}>{weightTotal}</span>
        </p>
        {Object.entries(config.weights).map(([key, value]) => (
          <div key={key} className="flex items-center gap-3">
            <label className="text-sm capitalize w-40">{key.replace(/_/g, " ")}</label>
            <input
              type="number"
              min={0}
              max={100}
              value={value}
              onChange={(e) =>
                setConfig({ ...config, weights: { ...config.weights, [key]: Number(e.target.value) } })
              }
              className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm w-24"
            />
          </div>
        ))}
      </section>

      <section className="rounded-lg border border-slate-800 bg-slate-900 p-4 space-y-3">
        <h2 className="font-semibold">Classification thresholds</h2>
        {Object.entries(config.thresholds).map(([key, value]) => (
          <div key={key} className="flex items-center gap-3">
            <label className="text-sm capitalize w-40">{key}</label>
            <input
              type="number"
              min={0}
              max={100}
              value={value}
              onChange={(e) =>
                setConfig({ ...config, thresholds: { ...config.thresholds, [key]: Number(e.target.value) } })
              }
              className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm w-24"
            />
          </div>
        ))}
      </section>

      <section className="rounded-lg border border-slate-800 bg-slate-900 p-4 space-y-3">
        <h2 className="font-semibold">Gating</h2>
        <div className="flex items-center gap-3">
          <label className="text-sm w-56">Minimum signal score to alert</label>
          <input
            type="number"
            min={0}
            max={100}
            value={config.min_signal_score}
            onChange={(e) => setConfig({ ...config, min_signal_score: Number(e.target.value) })}
            className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm w-24"
          />
        </div>
        <div className="flex items-center gap-3">
          <label className="text-sm w-56">Minimum R:R to Target 1</label>
          <input
            type="number"
            step={0.1}
            value={config.risk_policy.min_risk_reward_t1}
            onChange={(e) =>
              setConfig({ ...config, risk_policy: { ...config.risk_policy, min_risk_reward_t1: Number(e.target.value) } })
            }
            className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm w-24"
          />
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={config.risk_policy.suppress_on_critical_conflict}
            onChange={(e) =>
              setConfig({
                ...config,
                risk_policy: { ...config.risk_policy, suppress_on_critical_conflict: e.target.checked },
              })
            }
          />
          Suppress alerts outright on CRITICAL conflicting news
        </label>
      </section>

      <button onClick={save} className="bg-sky-600 hover:bg-sky-500 rounded-md px-4 py-2 text-sm font-medium">
        {saved ? "Saved ✓" : "Save scoring settings"}
      </button>

      <section className="rounded-lg border border-slate-800 bg-slate-900 p-4 space-y-3">
        <h2 className="font-semibold">Notification channels</h2>
        {prefs.map((p) => (
          <label key={p.channel} className="flex items-center gap-2 text-sm capitalize">
            <input type="checkbox" checked={p.enabled} onChange={() => togglePref(p)} />
            {p.channel.replace("_", "-")}
          </label>
        ))}
        <p className="text-xs text-slate-500">
          Email/Telegram credentials are configured via environment variables (see .env.example) — this toggle
          only controls whether the channel is used, not its credentials.
        </p>
      </section>
    </div>
  );
}
