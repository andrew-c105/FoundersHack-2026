import { useEffect, useMemo, useState } from "react";
import CalendarHeatmap from "react-calendar-heatmap";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, type PredictionRow, type SignalRow } from "../api";

type Tab = "heatmap" | "day" | "alerts";

function dateKey(dt: string) {
  return dt.slice(0, 10);
}

export default function MonthlyForecast() {
  const id = localStorage.getItem("locationId")!;
  const [tab, setTab] = useState<Tab>("heatmap");
  const [preds, setPreds] = useState<PredictionRow[]>([]);
  const [alerts, setAlerts] = useState<PredictionRow[]>([]);
  const [day, setDay] = useState<string>(() => new Date().toISOString().slice(0, 10));
  const [selHour, setSelHour] = useState<PredictionRow | null>(null);
  const [hourSignals, setHourSignals] = useState<SignalRow[]>([]);

  useEffect(() => {
    api.predictions(id).then(setPreds).catch(() => setPreds([]));
    api.alerts(id).then(setAlerts).catch(() => setAlerts([]));
  }, [id]);

  const heatmapValues = useMemo(() => {
    const m: Record<string, number> = {};
    for (const p of preds) {
      const d = dateKey(p.forecast_dt);
      m[d] = Math.max(m[d] || 0, Math.abs(p.deviation_pct));
    }
    return Object.entries(m).map(([date, v]) => ({
      date,
      count: Math.min(4, Math.ceil(v / 15)),
    }));
  }, [preds]);

  const startDate = useMemo(() => {
    if (!preds.length) return new Date();
    const t = preds[0].forecast_dt.slice(0, 10);
    return new Date(t + "T12:00:00");
  }, [preds]);

  const endDate = useMemo(() => {
    if (!preds.length) return new Date();
    const t = preds[preds.length - 1].forecast_dt.slice(0, 10);
    return new Date(t + "T12:00:00");
  }, [preds]);

  const dayRows = useMemo(
    () => preds.filter((p) => dateKey(p.forecast_dt) === day).sort((a, b) => a.forecast_dt.localeCompare(b.forecast_dt)),
    [preds, day]
  );

  useEffect(() => {
    if (!selHour) {
      setHourSignals([]);
      return;
    }
    api.signalsHour(id, selHour.forecast_dt).then(setHourSignals).catch(() => setHourSignals([]));
  }, [id, selHour]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-white">Monthly forecast</h1>
        <p className="text-sm text-slate-400">30-day hourly heatmap, day drill-down, and staffing alerts.</p>
      </div>

      <div className="flex gap-2 border-b border-slate-800 pb-2">
        {(["heatmap", "day", "alerts"] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`rounded-lg px-4 py-2 text-sm capitalize ${
              tab === t ? "bg-cyan-500/20 text-cyan-200" : "text-slate-400 hover:text-white"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "heatmap" && (
        <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/50 p-4">
          {heatmapValues.length === 0 ? (
            <p className="text-slate-500">No predictions yet.</p>
          ) : (
            <CalendarHeatmap
              startDate={startDate}
              endDate={endDate}
              values={heatmapValues}
              classForValue={(v) => {
                if (!v || !v.count) return "color-empty";
                return `color-scale-${v.count}`;
              }}
              tooltipDataAttrs={(v: { date?: string; count?: number } | null) =>
                v?.date
                  ? { "data-tip": `${v.date}: intensity ${v.count}` }
                  : {}
              }
            />
          )}
          <div className="mt-4 flex gap-4 text-xs text-slate-500">
            <span className="flex items-center gap-1">
              <span className="inline-block h-3 w-3 rounded bg-slate-800" /> calmer
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block h-3 w-3 rounded bg-cyan-900" />
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block h-3 w-3 rounded bg-cyan-600" /> busier vs normal
            </span>
          </div>
        </div>
      )}

      {tab === "day" && (
        <div className="space-y-4">
          <label className="flex items-center gap-2 text-sm text-slate-300">
            Date
            <input
              type="date"
              value={day}
              onChange={(e) => setDay(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1 text-white"
            />
          </label>
          <div className="h-72 rounded-2xl border border-slate-800 bg-slate-900/40 p-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dayRows.map((r) => ({ ...r, h: r.forecast_dt.slice(11, 16) }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="h" tick={{ fill: "#94a3b8", fontSize: 10 }} />
                <YAxis tick={{ fill: "#94a3b8" }} />
                <Tooltip
                  contentStyle={{ background: "#0f172a", border: "1px solid #334155" }}
                  labelStyle={{ color: "#e2e8f0" }}
                />
                <Bar dataKey="busyness_index" fill="#06b6d4" name="Index">
                  {dayRows.map((entry) => (
                    <Cell
                      key={entry.forecast_dt}
                      cursor="pointer"
                      onClick={() => setSelHour(entry)}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="text-xs text-slate-500">Click a bar to load drivers for that hour.</p>
          {selHour && (
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <p className="text-sm font-medium text-cyan-200">{selHour.forecast_dt}</p>
              <ul className="mt-2 space-y-1 text-sm text-slate-300">
                {hourSignals.length === 0 && <li>No processed signals for this hour.</li>}
                {hourSignals.map((s) => (
                  <li key={`${s.signal_type}-${s.label}`}>
                    <span className="text-slate-400">{s.signal_type}</span> — {s.label || "—"} (
                    {(s.uplift_pct * 100).toFixed(1)}% uplift, conf {s.confidence})
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {tab === "alerts" && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50">
          <div className="border-b border-slate-800 px-4 py-3">
            <h2 className="font-display font-semibold text-white">Hours ≥ +30% vs normal</h2>
          </div>
          <ul className="max-h-[480px] divide-y divide-slate-800 overflow-auto">
            {alerts.length === 0 && <li className="px-4 py-6 text-slate-500">No alert hours in this window.</li>}
            {alerts.map((a) => (
              <li key={a.forecast_dt} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm">
                <span className="text-slate-200">{a.forecast_dt}</span>
                <span className="text-amber-300">+{a.deviation_pct}%</span>
                <span className="text-slate-500">index {a.busyness_index}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
