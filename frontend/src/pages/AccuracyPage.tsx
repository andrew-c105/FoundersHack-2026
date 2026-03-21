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
        <h1 className="font-display text-2xl font-bold text-gray-900">Accuracy history</h1>
        <p className="text-sm text-gray-500">
          Daily average predicted index vs Popular Times baseline (proxy for “actual” rhythm).
        </p>
      </div>
      {lastMae != null && (
        <div className="rounded-2xl border border-gray-100 bg-white shadow-sm px-5 py-4 text-sm text-gray-700">
          Last training MAE (hold-out): <span className="font-mono text-blue-600 font-semibold">{lastMae.toFixed(2)}</span>{" "}
          busyness points
        </div>
      )}
      <div className="h-[22rem] rounded-2xl border border-gray-100 bg-white shadow-sm p-4">
        {byDay.length === 0 ? (
          <p className="p-4 text-gray-500">No prediction data.</p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={byDay}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="date" tick={{ fill: "#64748b", fontSize: 10 }} />
              <YAxis tick={{ fill: "#64748b" }} domain={[0, 100]} />
              <Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "8px" }} labelStyle={{ color: "#0f172a", fontWeight: "bold", marginBottom: "4px" }} />
              <Legend wrapperStyle={{ paddingTop: "20px" }} />
              <Line type="monotone" dataKey="predicted" stroke="#3b82f6" strokeWidth={2} dot={false} name="Predicted avg" />
              <Line type="monotone" dataKey="baseline" stroke="#94a3b8" strokeWidth={2} dot={false} name="Baseline avg" />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
