import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, type PredictionRow } from "../api";

function dateKey(dt: string) {
  return dt.slice(0, 10);
}

export default function AccuracyPage() {
  const id = localStorage.getItem("locationId")!;
  const [preds, setPreds] = useState<PredictionRow[]>([]);
  const [hist, setHist] = useState<{ mae: number; evaluated_at: string }[]>([]);

  useEffect(() => {
    api.predictions(id).then(setPreds).catch(() => setPreds([]));
    api.accuracy(id).then((r) => setHist(r.history)).catch(() => setHist([]));
  }, [id]);

  const byDay = useMemo(() => {
    const m: Record<string, { pred: number; base: number; n: number }> = {};
    for (const p of preds) {
      const d = dateKey(p.forecast_dt);
      if (!m[d]) m[d] = { pred: 0, base: 0, n: 0 };
      m[d].pred += p.busyness_index;
      m[d].base += p.baseline_score;
      m[d].n += 1;
    }
    return Object.entries(m)
      .map(([date, v]) => ({
        date,
        predicted: Math.round(v.pred / v.n),
        baseline: Math.round(v.base / v.n),
      }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [preds]);

  const lastMae = hist[0]?.mae;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-white">Accuracy history</h1>
        <p className="text-sm text-slate-400">
          Daily average predicted index vs Popular Times baseline (proxy for “actual” rhythm).
        </p>
      </div>
      {lastMae != null && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 px-4 py-3 text-sm">
          Last training MAE (hold-out): <span className="font-mono text-cyan-300">{lastMae.toFixed(2)}</span>{" "}
          busyness points
        </div>
      )}
      <div className="h-80 rounded-2xl border border-slate-800 bg-slate-900/40 p-2">
        {byDay.length === 0 ? (
          <p className="p-4 text-slate-500">No prediction data.</p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={byDay}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 10 }} />
              <YAxis tick={{ fill: "#94a3b8" }} domain={[0, 100]} />
              <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
              <Legend />
              <Line type="monotone" dataKey="predicted" stroke="#22d3ee" dot={false} name="Predicted avg" />
              <Line type="monotone" dataKey="baseline" stroke="#64748b" dot={false} name="Baseline avg" />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
