import { useEffect, useMemo, useState } from "react";
import CalendarHeatmap from "react-calendar-heatmap";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, type PredictionRow, type DaySignal } from "../api";

type Tab = "heatmap" | "day";

function dateKey(dt: string) {
  return dt.slice(0, 10);
}

function fmtHour(h: number) {
  return `${String(h).padStart(2, "0")}:00`;
}

function signalTypeLabel(st: string) {
  const m: Record<string, string> = {
    ticketmaster: "event",
    eventbrite: "event",
    open_meteo: "weather",
    google_places: "competitor",
    transport_nsw: "transport",
    live_traffic: "transport",
    static_sport: "sport",
    static_school: "school holiday",
    static_holiday: "public holiday",
    static_uni: "university",
    static: "static",
  };
  return m[st] || st;
}

export default function MonthlyForecast() {
  const id = localStorage.getItem("locationId")!;
  const [tab, setTab] = useState<Tab>("heatmap");
  const [preds, setPreds] = useState<PredictionRow[]>([]);
  const [day, setDay] = useState<string>(() => new Date().toISOString().slice(0, 10));
  const [daySignals, setDaySignals] = useState<DaySignal[]>([]);
  const [dayBrief, setDayBrief] = useState("");
  const [posCount, setPosCount] = useState(0);
  const [negCount, setNegCount] = useState(0);

  useEffect(() => {
    api.predictions(id).then(setPreds).catch(() => setPreds([]));
  }, [id]);

  // Fetch day-level signals when the date or tab changes
  useEffect(() => {
    if (tab !== "day") return;
    api
      .signalsDay(id, day)
      .then((r) => {
        setDaySignals(r.signals);
        setDayBrief(r.brief);
        setPosCount(r.positive_count);
        setNegCount(r.negative_count);
      })
      .catch(() => {
        setDaySignals([]);
        setDayBrief("");
      });
  }, [id, day, tab]);

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
    () =>
      preds
        .filter((p) => dateKey(p.forecast_dt) === day)
        .sort((a, b) => a.forecast_dt.localeCompare(b.forecast_dt)),
    [preds, day]
  );

  // Compute peak period from predictions
  const peakPeriod = useMemo(() => {
    if (!dayRows.length) return "";
    let maxIdx = 0;
    for (let i = 1; i < dayRows.length; i++) {
      if (dayRows[i].busyness_index > dayRows[maxIdx].busyness_index) maxIdx = i;
    }
    const peakH = parseInt(dayRows[maxIdx].forecast_dt.slice(11, 13), 10);
    // Find contiguous peak window (hours within 80% of max)
    const threshold = dayRows[maxIdx].busyness_index * 0.8;
    let startH = peakH, endH = peakH;
    for (const r of dayRows) {
      const h = parseInt(r.forecast_dt.slice(11, 13), 10);
      if (r.busyness_index >= threshold) {
        if (h < startH) startH = h;
        if (h > endH) endH = h;
      }
    }
    return `${fmtHour(startH)}–${fmtHour(endH)}`;
  }, [dayRows]);

  const dayLabel = useMemo(() => {
    const d = new Date(day + "T12:00:00");
    return d.toLocaleDateString("en-AU", { weekday: "long", day: "numeric", month: "short" });
  }, [day]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-white">Monthly forecast</h1>
        <p className="text-sm text-slate-400">30-day heatmap and day-level signal breakdown.</p>
      </div>

      <div className="flex gap-2 border-b border-slate-800 pb-2">
        {(["heatmap", "day"] as const).map((t) => (
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
          {/* Date picker */}
          <label className="flex items-center gap-2 text-sm text-slate-300">
            Date
            <input
              type="date"
              value={day}
              onChange={(e) => setDay(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1 text-white"
            />
          </label>

          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-display text-xl font-bold text-white">
                {dayLabel} — all signals
              </h2>
              <p className="text-sm text-slate-400">
                {daySignals.length} signals active today
                {peakPeriod && ` · peak period ${peakPeriod}`}
              </p>
            </div>
            <div className="flex gap-2">
              {posCount > 0 && (
                <span className="rounded-full bg-emerald-500/20 px-3 py-1 text-xs font-medium text-emerald-300">
                  {posCount} positive
                </span>
              )}
              {negCount > 0 && (
                <span className="rounded-full bg-red-500/20 px-3 py-1 text-xs font-medium text-red-300">
                  {negCount} negative
                </span>
              )}
            </div>
          </div>

          {/* Bar chart */}
          <div className="h-56 rounded-2xl border border-slate-800 bg-slate-900/40 p-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dayRows.map((r) => ({ ...r, h: r.forecast_dt.slice(11, 16) }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="h" tick={{ fill: "#94a3b8", fontSize: 10 }} />
                <YAxis tick={{ fill: "#94a3b8" }} />
                <Tooltip
                  contentStyle={{ background: "#0f172a", border: "1px solid #334155" }}
                  labelStyle={{ color: "#e2e8f0" }}
                />
                <Bar dataKey="busyness_index" fill="#06b6d4" name="Index" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Signal timeline cards */}
          <div className="space-y-3">
            {daySignals.length === 0 && (
              <p className="text-sm text-slate-500">No signals for this date. Try refreshing signals in Settings.</p>
            )}
            
            {/* Sort: Positives first (largest to smallest), then negatives (largest magnitude to smallest) */}
            {[...daySignals]
              .sort((a, b) => {
                if (a.uplift_pct >= 0 && b.uplift_pct < 0) return -1;
                if (a.uplift_pct < 0 && b.uplift_pct >= 0) return 1;
                return Math.abs(b.uplift_pct) - Math.abs(a.uplift_pct);
              })
              .map((sig) => (
                sig.signal_type === "open_meteo" ? (
                  <WeatherCard key={sig.label} signal={sig} />
                ) : (
                  <SignalCard key={sig.label} signal={sig} />
                )
            ))}
          </div>

          {/* Net outlook */}
          {dayBrief && (
            <div className="rounded-xl border border-slate-700/60 bg-slate-900/40 px-5 py-4">
              <p className="text-sm leading-relaxed text-slate-300">
                <span className="font-semibold text-slate-200">Net outlook: </span>
                {dayBrief}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}


/* ── Weather Card ────────────────────────────── */

function WeatherCard({ signal }: { signal: DaySignal }) {
  const isPositive = signal.uplift_pct >= 0;
  const dotColor = isPositive ? "bg-emerald-400" : "bg-red-400";
  const upliftColor = isPositive
    ? "bg-emerald-500/20 text-emerald-300"
    : "bg-red-500/20 text-red-300";

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      {/* Top row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className={`mt-0.5 inline-block h-2.5 w-2.5 rounded-full ${dotColor}`} />
            <h3 className="font-display font-semibold text-white">{signal.label}</h3>
          </div>
          <div className="flex gap-4 pl-4 text-xs text-slate-400">
            <span>{signal.temp_low}°C – {signal.temp_high}°C</span>
            <span>{signal.total_rain_mm}mm rain</span>
            <span>{signal.conditions}</span>
          </div>
        </div>
        
        <div className="flex flex-col items-end gap-1 text-xs">
          <span className={`rounded-full px-2.5 py-0.5 font-semibold ${upliftColor}`}>
            {isPositive ? "+" : ""}
            {Math.round(signal.uplift_pct * 100)}% uplift
          </span>
          <span className="text-slate-500 mr-1">conf {signal.confidence}</span>
        </div>
      </div>

      {signal.description && (
        <p className="mt-3 pl-4 text-sm leading-relaxed text-slate-300">
          {signal.description}
        </p>
      )}

      {/* Outlier warning row */}
      {signal.outlier && (
        <div className="mt-3 ml-4 rounded border border-amber-900/50 bg-amber-950/30 px-3 py-2 text-sm text-amber-200">
          <span className="font-semibold">{signal.outlier_label}</span> expected between {signal.outlier_hours}
        </div>
      )}

      {/* Timeline bar */}
      <div className="mt-4 ml-4">
        <div className="relative h-2 rounded-full bg-slate-800 overflow-hidden">
          {/* Base bar showing trading hours */}
          <div
            className={`absolute top-0 h-full bg-slate-700`}
            style={{ left: "0%", width: "100%" }}
          />
          {/* Outlier timeline block overlay */}
          {signal.outlier && signal.outlier_hours && (
            <div
              className="absolute top-0 h-full bg-amber-600/60"
              style={{
                left: `${((parseInt(signal.outlier_hours.slice(0, 2)) - 6) / 17) * 100}%`,
                width: `${
                  ((parseInt(signal.outlier_hours.slice(6, 8)) - parseInt(signal.outlier_hours.slice(0, 2))) / 17) * 100
                }%`,
              }}
            />
          )}
        </div>
        <div className="mt-1.5 flex justify-between text-[10px] text-slate-500">
          {[6, 9, 12, 15, 18, 21, 23].map((h) => (
            <span key={h}>{fmtHour(h)}</span>
          ))}
        </div>
      </div>
    </div>
  );
}


/* ── Signal card with timeline bar ────────────────────────────── */

function SignalCard({ signal }: { signal: DaySignal }) {
  const isPositive = signal.uplift_pct >= 0;
  const dotColor = isPositive ? "bg-emerald-400" : "bg-red-400";
  const upliftColor = isPositive
    ? "bg-emerald-500/20 text-emerald-300"
    : "bg-red-500/20 text-red-300";
  const barColor = isPositive ? "bg-emerald-500/60" : "bg-red-500/50";

  // Calculate bar position as percentage of 6:00-23:00 range
  const rangeStart = 6;
  const rangeEnd = 23;
  const totalHours = rangeEnd - rangeStart;
  const leftPct = Math.max(0, ((signal.start_hour - rangeStart) / totalHours) * 100);
  const widthPct = Math.min(100 - leftPct, ((signal.end_hour - signal.start_hour + 1) / totalHours) * 100);
  const isAllDay = signal.start_hour <= rangeStart && signal.end_hour >= rangeEnd - 1;
  const timeLabel = isAllDay
    ? "Active all day"
    : `Active ${fmtHour(signal.start_hour)} – ${fmtHour(signal.end_hour + 1)}`;

  const ticks = [6, 9, 12, 15, 18, 21, 23];

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      {/* Top row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className={`mt-1 inline-block h-2.5 w-2.5 rounded-full ${dotColor}`} />
          <h3 className="font-display font-semibold text-white">{signal.label}</h3>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded bg-slate-700/60 px-2 py-0.5 text-slate-300">
            {signalTypeLabel(signal.signal_type)}
          </span>
          <span className={`rounded-full px-2.5 py-0.5 font-semibold ${upliftColor}`}>
            {isPositive ? "+" : ""}
            {Math.round(signal.uplift_pct * 100)}% uplift
          </span>
          <span className="text-slate-500 mr-1">conf {signal.confidence}</span>
        </div>
      </div>

      {/* Description / Additional details */}
      <div className="mt-1 pl-4">
        {signal.distance_km != null && (
          <p className="text-sm text-slate-400">
            {signal.distance_km}km away
          </p>
        )}
        {signal.description && (
          <p className="mt-1 text-sm text-slate-300 leading-relaxed">
            {signal.description}
          </p>
        )}
      </div>

      {/* Timeline bar */}
      <div className="mt-4 pl-4">
        <div className="relative h-2 rounded-full bg-slate-800">
          <div
            className={`absolute top-0 h-full rounded-full ${barColor}`}
            style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
          />
        </div>
        <div className="mt-1.5 flex justify-between text-[10px] text-slate-500">
          {ticks.map((h) => (
            <span key={h}>{fmtHour(h)}</span>
          ))}
        </div>
        <p className="mt-1 text-xs text-slate-400">{timeLabel}</p>
      </div>
    </div>
  );
}
