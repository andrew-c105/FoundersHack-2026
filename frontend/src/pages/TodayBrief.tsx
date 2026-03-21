import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, type SignalRow } from "../api";

export default function TodayBrief() {
  const id = localStorage.getItem("locationId")!;
  const [brief, setBrief] = useState<string>("");
  const [peak, setPeak] = useState<Record<string, unknown> | null>(null);
  const [signals, setSignals] = useState<SignalRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const b = await api.brief(id);
        if (cancelled) return;
        setBrief(b.brief);
        setPeak(b.peak_hour as Record<string, unknown> | null);
        if (b.peak_hour) {
          const s = await api.signalsHour(id, String(b.peak_hour.forecast_dt));
          setSignals(s);
        }
      } catch {
        setBrief("Could not load brief. Try refreshing signals in Settings.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  const chartData = signals.map((s) => ({
    name: (s.label || s.signal_type).slice(0, 18),
    uplift: Math.round((s.uplift_pct || 0) * 100),
  }));

  if (loading) return <p className="text-slate-400">Loading brief…</p>;

  const bi = peak ? Number(peak.busyness_index) : "—";
  const dev = peak ? Number(peak.deviation_pct) : "—";
  const conf = peak ? Number(peak.confidence) : "—";

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-bold text-white">Today&apos;s brief</h1>
        <p className="text-sm text-slate-400">Plain-language summary from structured forecast data.</p>
      </div>

      <motion.article
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 leading-relaxed text-slate-200"
      >
        {brief}
      </motion.article>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Busyness index", value: bi },
          { label: "Deviation vs normal", value: dev === "—" ? "—" : `${dev}%` },
          { label: "Confidence", value: conf === "—" ? "—" : conf },
          { label: "Peak hour", value: peak ? String(peak.forecast_dt).replace("T", " ").slice(0, 16) : "—" },
        ].map((c) => (
          <div key={c.label} className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">{c.label}</p>
            <p className="mt-1 font-display text-2xl font-semibold text-cyan-300">{c.value}</p>
          </div>
        ))}
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
        <h2 className="mb-4 font-display text-lg font-semibold text-white">Signals at peak hour</h2>
        <div className="h-64 w-full">
          {chartData.length ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <YAxis tick={{ fill: "#94a3b8" }} />
                <Tooltip
                  contentStyle={{ background: "#0f172a", border: "1px solid #334155" }}
                  labelStyle={{ color: "#e2e8f0" }}
                />
                <Bar dataKey="uplift" fill="#22d3ee" radius={[4, 4, 0, 0]} name="Uplift %" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-slate-500">No signal rows for peak hour.</p>
          )}
        </div>
      </div>

      <button
        type="button"
        className="rounded-xl border border-cyan-600/50 px-4 py-2 text-sm text-cyan-200 hover:bg-cyan-500/10"
        onClick={() => alert("Wire-up: POST schedule approval to your roster tool.")}
      >
        Approve suggested schedule (demo)
      </button>
    </div>
  );
}
