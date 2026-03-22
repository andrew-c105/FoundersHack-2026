import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import CalendarHeatmap from "react-calendar-heatmap";
import "react-calendar-heatmap/dist/styles.css";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
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

/** Backend stores UTC hour buckets as `YYYY-MM-DDTHH:MM:00` without a zone suffix. */
function parseUtcForecastInstant(forecast_dt: string): Date {
  const raw = forecast_dt.trim();
  if (raw.length === 10) {
    return new Date(`${raw}T00:00:00Z`);
  }
  const hasZone =
    raw.endsWith("Z") || /[+-]\d{2}:?\d{2}$/.test(raw);
  const iso = !hasZone && raw.length >= 19 ? `${raw.slice(0, 19)}Z` : raw;
  return new Date(iso);
}

/** Calendar date in Australia/Sydney for a prediction row (matches date picker). */
function sydneyDateKeyFromForecastDt(forecast_dt: string): string {
  return parseUtcForecastInstant(forecast_dt).toLocaleDateString("en-CA", {
    timeZone: "Australia/Sydney",
  });
}

function sydneyHourFromForecastDt(forecast_dt: string): number {
  const d = parseUtcForecastInstant(forecast_dt);
  const parts = new Intl.DateTimeFormat("en-AU", {
    timeZone: "Australia/Sydney",
    hour: "2-digit",
    hour12: false,
  }).formatToParts(d);
  const h = parts.find((p) => p.type === "hour")?.value;
  return h != null ? parseInt(h, 10) : 0;
}

function localCalendarDateKey(d = new Date()): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function fmtHour(h: number) {
  return `${String(h).padStart(2, "0")}:00`;
}

function signalTypeLabel(st: string) {
  const m: Record<string, string> = {
    ticketmaster: "event",
    eventbrite: "event",
    sporting_event: "sport",
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

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 15 },
  show: { opacity: 1, y: 0 }
};

export default function TodayBrief() {
  const id = localStorage.getItem("locationId")!;
  const [day, setDay] = useState<string>(() => localCalendarDateKey());

  const [brief, setBrief] = useState<string>("");
  const [peak, setPeak] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  const [preds, setPreds] = useState<PredictionRow[]>([]);
  const [daySignals, setDaySignals] = useState<DaySignal[]>([]);
  const [dayBrief, setDayBrief] = useState("");
  const [posCount, setPosCount] = useState(0);
  const [negCount, setNegCount] = useState(0);

  useEffect(() => {
    api.predictions(id).then(setPreds).catch(() => setPreds([]));
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        const b = await api.brief(id, day);
        if (cancelled) return;
        setBrief(b.brief);
        setPeak(b.peak_hour as Record<string, unknown> | null);
      } catch {
        if (!cancelled) setBrief("Could not load brief. Try refreshing signals in Settings.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id, day]);

  useEffect(() => {
    let cancelled = false;
    api
      .signalsDay(id, day)
      .then((r) => {
        if (cancelled) return;
        const processed = r.signals.map((s: any) => {
          return {
            ...s,
            label: s.outlier_label ? `Weather: ${s.outlier_label}` : s.label,
            start_hour: s.start_hour ?? (s.signal_type.includes("event") ? 18 : 9),
            end_hour: s.end_hour ?? (s.signal_type.includes("event") ? 22 : 17),
            outlier: s.outlier || false,
            outlier_alert: s.outlier_alert || null,
            low_temp: s.low_temp ?? s.temp_low,
            high_temp: s.high_temp ?? s.temp_high,
            rainfall_mm: s.rainfall_mm ?? s.total_rain_mm,
            conditions: s.conditions,
            description: s.description || null,
          };
        });
        setDaySignals(processed);
        setDayBrief(r.brief);
        setPosCount(r.positive_count);
        setNegCount(r.negative_count);
      })
      .catch(() => {
        if (cancelled) return;
        setDaySignals([]);
        setDayBrief("");
      });
    return () => {
      cancelled = true;
    };
  }, [id, day]);

  const heatmapValues = useMemo(() => {
    const m: Record<string, number> = {};
    for (const p of preds) {
      const d = sydneyDateKeyFromForecastDt(p.forecast_dt);
      m[d] = Math.max(m[d] || 0, Math.abs(p.deviation_pct));
    }
    return Object.entries(m).map(([date, v]) => ({
      date,
      count: Math.min(4, Math.ceil(v / 15)),
    }));
  }, [preds]);

  const startDate = useMemo(() => {
    const d = new Date();
    d.setFullYear(d.getFullYear() - 1);
    d.setDate(d.getDate() + 60);
    return d;
  }, []);

  const endDate = useMemo(() => {
    const d = new Date();
    d.setDate(d.getDate() + 70);
    return d;
  }, []);

  const dayRows = useMemo(
    () =>
      preds
        .filter((p) => sydneyDateKeyFromForecastDt(p.forecast_dt) === day)
        .sort((a, b) => a.forecast_dt.localeCompare(b.forecast_dt)),
    [preds, day]
  );

  const peakPeriod = useMemo(() => {
    if (!dayRows.length) return "";
    let maxIdx = 0;
    for (let i = 1; i < dayRows.length; i++) {
      if (dayRows[i].busyness_index > dayRows[maxIdx].busyness_index) maxIdx = i;
    }
    const peakH = sydneyHourFromForecastDt(dayRows[maxIdx].forecast_dt);
    const threshold = dayRows[maxIdx].busyness_index * 0.8;
    let startH = peakH, endH = peakH;
    for (const r of dayRows) {
      const h = sydneyHourFromForecastDt(r.forecast_dt);
      if (r.busyness_index >= threshold) {
        if (h < startH) startH = h;
        if (h > endH) endH = h;
      }
    }
    return `${fmtHour(startH)}–${fmtHour(endH)}`;
  }, [dayRows]);

  const dayLabel = useMemo(() => {
    const d = new Date(day + "T12:00:00");
    const isToday = day === localCalendarDateKey();
    return isToday ? `Today (${d.toLocaleDateString("en-AU", { weekday: "short", day: "numeric", month: "short" })})` : d.toLocaleDateString("en-AU", { weekday: "long", day: "numeric", month: "short" });
  }, [day]);

  if (loading && !brief) return <p className="text-gray-500">Loading dashboard…</p>;

  const bi = peak ? Number(peak.busyness_index) : "—";
  const dev = peak ? Number(peak.deviation_pct) : "—";
  const conf = peak ? Number(peak.forecast_confidence) : "—";

  return (
    <>
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="show"
        className="max-w-[1400px] mx-auto space-y-10 pb-20"
      >
        <motion.div variants={itemVariants} className="flex items-center justify-between">
          <div className="flex flex-col gap-1">
            <h1 className="font-display text-3xl font-extrabold tracking-tight text-gray-900">{dayLabel}</h1>
            <p className="text-sm text-gray-500">Plain-language summary and specific signals for chosen date.</p>
          </div>
          <label className="flex items-center gap-3 text-sm font-semibold text-gray-600">
            Target Date
            <DatePicker
              selected={new Date(day + "T12:00:00")}
              onChange={(date: Date | null) => {
                if (date) {
                  const yyyy = date.getFullYear();
                  const mm = String(date.getMonth() + 1).padStart(2, '0');
                  const dd = String(date.getDate()).padStart(2, '0');
                  setDay(`${yyyy}-${mm}-${dd}`);
                }
              }}
              dateFormat="dd/MM/yyyy"
              className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 shadow-sm outline-none focus:border-blue-600 focus:ring-1 focus:ring-blue-600 transition w-32 font-semibold"
            />
          </label>
        </motion.div>

        {brief && (
          <motion.article
            variants={itemVariants}
            className="rounded-2xl border border-gray-100 bg-white shadow-sm p-6 leading-relaxed text-gray-700"
          >
            {brief.replace(/\d{4}-\d{2}-\d{2}T(\d{2}):\d{2}:\d{2}/g, (match) => {
              const date = new Date(match);
              return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });
            })}
          </motion.article>
        )}

        <motion.div variants={itemVariants} className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {[
            {
              label: "Busyness index",
              value: bi,
              tooltip: "Absolute busyness score (0-100) based on typical peak capacity."
            },
            {
              label: "Deviation vs normal",
              value: dev === "—" ? "—" : `${dev > 0 ? '+' : ''}${dev}%`,
              tooltip: "How much busier (+) or quieter (-) this hour is compared to your location's historical average for this specific time and day."
            },
            {
              label: "Confidence",
              value: conf === "—" ? "—" : `${Math.round(conf * 100)}%`,
              tooltip: "The statistical certainty of this prediction based on data quality and signal strength."
            },
            {
              label: "Peak hour",
              value: peak
                ? parseUtcForecastInstant(String(peak.forecast_dt)).toLocaleTimeString("en-AU", {
                    timeZone: "Australia/Sydney",
                    hour: "numeric",
                    minute: "2-digit",
                    hour12: true,
                  })
                : "—",
              tooltip: "The specific hour during this 24-hour period expected to have the highest foot traffic."
            },
          ].map((c) => (
            <div
              key={c.label}
              className="group relative rounded-2xl border border-gray-100 bg-white shadow-sm p-6 flex flex-col items-start justify-between transition hover:border-blue-200 hover:shadow-md"
            >
              <div className="flex items-center gap-1.5">
                <p className="text-sm font-medium text-gray-500 shrink-0">{c.label}</p>
              </div>

              {/* Tooltip implementation via CSS or simple absolute div */}
              <div className="absolute bottom-full left-1/2 mb-2 hidden w-48 -translate-x-1/2 rounded-lg bg-gray-900 px-3 py-2 text-center text-xs text-white shadow-xl group-hover:block z-50">
                {c.tooltip}
                <div className="absolute top-full left-1/2 -ml-1 border-4 border-transparent border-t-gray-900" />
              </div>

              <p className={`mt-4 text-3xl font-bold ${c.label === 'Deviation vs normal' && typeof c.value === 'string' && c.value.includes('-') ? 'text-red-500' : 'text-blue-600'}`}>
                {c.value}
              </p>
            </div>
          ))}
        </motion.div>

        <motion.div variants={itemVariants} className="space-y-8">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-display text-xl font-bold text-gray-900">
                {dayLabel} — active signals
              </h2>
              <p className="text-sm text-gray-500">
                {daySignals.length} signals active today
                {peakPeriod && ` · peak period ${peakPeriod}`}
              </p>
            </div>
            <div className="flex gap-2">
              {posCount > 0 && (
                <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700">
                  {posCount} positive
                </span>
              )}
              {negCount > 0 && (
                <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-medium text-red-700">
                  {negCount} negative
                </span>
              )}
            </div>
          </div>

          {/* Bar chart from day view */}
          <div className="h-56 rounded-2xl border border-gray-100 bg-white shadow-sm p-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={dayRows.map((r) => ({
                  ...r,
                  h: `${String(sydneyHourFromForecastDt(r.forecast_dt)).padStart(2, "0")}:00`,
                }))}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="h" tick={{ fill: "#64748b", fontSize: 10 }} />
                <YAxis tick={{ fill: "#64748b" }} />
                <Tooltip
                  contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.05)" }}
                  labelStyle={{ fontWeight: "bold", color: "#1e293b" }}
                />
                <Bar dataKey="busyness_index" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Signal timeline cards */}
          <div className="flex flex-col gap-6">
            {/* Sort: Positives first (largest to smallest), then negatives (largest magnitude to smallest) */}
            {[...daySignals]
              .filter((sig) => sig.signal_type !== "open_meteo" || (sig.impact_magnitude && sig.impact_magnitude > 0.05))
              .sort((a, b) => {
                if (a.uplift_pct >= 0 && b.uplift_pct < 0) return -1;
                if (a.uplift_pct < 0 && b.uplift_pct >= 0) return 1;
                return Math.abs(b.uplift_pct) - Math.abs(a.uplift_pct);
              })
              .map((sig, idx) => (
                <SignalCard key={idx} signal={sig} />
              ))}
          </div>

          {/* Net outlook */}
          {dayBrief && (
            <div className="rounded-2xl border border-gray-200 bg-gray-50 px-5 py-4">
              <p className="text-sm leading-relaxed text-gray-700">
                <span className="font-semibold text-gray-900">Net outlook: </span>
                {dayBrief}
              </p>
            </div>
          )}
        </motion.div>

        <motion.div variants={itemVariants} className="space-y-3">
          <h2 className="font-display text-xl font-bold text-gray-900">12-month forecast overview</h2>
          <div className="overflow-x-auto rounded-2xl border border-gray-100 bg-white shadow-sm p-5 pb-2">
            <div className="w-full mx-auto">
              {heatmapValues.length === 0 ? (
                <p className="text-gray-500">No predictions yet.</p>
              ) : (
                <CalendarHeatmap
                  startDate={startDate}
                  endDate={endDate}
                  values={heatmapValues}
                  classForValue={(v) => {
                    if (!v || !v.count) return "color-empty";
                    return `color-scale-${v.count}`;
                  }}
                  tooltipDataAttrs={(v: any) =>
                    (v?.date
                      ? { "data-tip": `${v.date}: intensity ${v.count}` }
                      : {}) as any
                  }
                />
              )}
              <div className="mt-4 flex justify-end items-center gap-1 text-xs text-gray-500">
                <span className="mr-1">Less</span>
                <span className="inline-block h-3 w-3 rounded-sm bg-[#f1f5f9]" />
                <span className="inline-block h-3 w-3 rounded-sm bg-[#dbeafe]" />
                <span className="inline-block h-3 w-3 rounded-sm bg-[#93c5fd]" />
                <span className="inline-block h-3 w-3 rounded-sm bg-[#3b82f6]" />
                <span className="inline-block h-3 w-3 rounded-sm bg-[#1d4ed8]" />
                <span className="ml-1">More</span>
              </div>
            </div>
          </div>
        </motion.div>
      </motion.div>

      <div className="pt-4 border-t border-gray-100 flex justify-end">
        <button
          type="button"
          className="rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 hover:-translate-y-0.5"
          onClick={() => alert("Wire-up: POST schedule approval to your roster tool.")}
        >
          Approve suggested schedule (demo)
        </button>
      </div>
    </>
  );
}



function SignalCard({ signal }: { signal: any }) {
  const isPositive = signal.uplift_pct >= 0;
  const isWeather = signal.signal_type === "open_meteo";
  const dotColor = isWeather ? "bg-amber-400" : (isPositive ? "bg-green-500" : "bg-red-500");
  const upliftColor = isPositive
    ? "bg-green-100 text-green-700"
    : "bg-red-100 text-red-700";
  const barColor = isWeather ? "bg-amber-400" : (isPositive ? "bg-green-500" : "bg-red-500");
  const cardBorder = isWeather ? "border-amber-200 bg-white" : (isPositive ? "border-gray-100 bg-white" : "border-red-100 bg-red-50/40");

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
    <div className={`rounded-2xl border ${cardBorder} shadow-sm p-4`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className={`mt-1 inline-block h-2.5 w-2.5 rounded-full ${dotColor}`} />
          <h3 className="font-display font-semibold text-gray-900">{signal.label}</h3>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded-md bg-gray-100 px-2.5 py-1 text-gray-600 font-medium">
            {signalTypeLabel(signal.signal_type)}
          </span>
          <span className={`rounded-full px-2.5 py-1 font-semibold ${upliftColor}`}>
            {isPositive ? "+" : ""}
            {Math.round(signal.uplift_pct * 100)}% {isPositive ? "uplift" : "impact"}
          </span>
          <span className="text-gray-400 mr-1">conf {signal.signal_conf}</span>
        </div>
      </div>

      <div className="mt-2 pl-4">
        {signal.distance_km != null && (
          <p className="text-sm font-medium text-gray-500 mb-1">
            {signal.distance_km}km away
          </p>
        )}
        
        {isWeather && (
          <div className="mt-2 mb-3 mr-4 grid grid-cols-4 gap-2">
            <div className="rounded-lg border border-gray-100 bg-gray-50/80 p-2 text-center">
               <span className="block text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-0.5">Low</span>
               <span className="text-sm font-bold text-gray-900">{signal.low_temp}°C</span>
            </div>
            <div className="rounded-lg border border-gray-100 bg-gray-50/80 p-2 text-center">
               <span className="block text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-0.5">High</span>
               <span className="text-sm font-bold text-gray-900">{signal.high_temp}°C</span>
            </div>
            <div className="rounded-lg border border-gray-100 bg-gray-50/80 p-2 text-center">
               <span className="block text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-0.5">Rain</span>
               <span className={`text-sm font-bold ${signal.rainfall_mm > 0 ? "text-amber-600" : "text-gray-900"}`}>{signal.rainfall_mm}mm</span>
            </div>
            <div className="rounded-lg border border-gray-100 bg-gray-50/80 p-2 text-center">
               <span className="block text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-0.5">Conditions</span>
               <span className={`text-sm font-bold ${signal.conditions?.toLowerCase().includes("rain") || signal.conditions?.toLowerCase().includes("storm") ? "text-amber-600" : "text-gray-900"}`}>{signal.conditions}</span>
            </div>
          </div>
        )}

        {isWeather && (signal.outlier_alert || signal.outlier) ? null : (
          <p className="mt-1 text-sm text-gray-600 leading-relaxed">
            {signal.description || (
              signal.signal_type === "sporting_event" || signal.signal_type === "static_sport"
                ? "Scheduled fixture at nearby stadium. Expect localized congestion."
                : signal.signal_type === "eventbrite" || signal.signal_type === "ticketmaster"
                  ? "Local ticketed event scheduled nearby."
                  : signal.signal_type === "google_places"
                    ? "Nearby place change may shift local demand."
                    : signal.signal_type === "live_traffic" || signal.signal_type === "transport_nsw"
                      ? "Transport disruption may affect pedestrian approach routes."
                      : signal.signal_type.includes("holiday")
                        ? "Public holiday driving significant changes to baselines."
                        : signal.signal_type.includes("school")
                          ? "School term impact period influencing foot traffic."
                          : signal.signal_type === "open_meteo" && signal.outlier
                            ? "Weather outlier detected, impacting foot traffic."
                            : "Model anomaly flag generated from location activity."
            )}
          </p>
        )}
      </div>

      {isWeather && (signal.outlier_alert || signal.outlier) && (
        <div className="mt-3 ml-4 mr-4 rounded-lg bg-amber-50/80 border border-amber-200/50 p-3">
           <p className="text-sm text-amber-900/90 font-medium leading-relaxed">{signal.outlier_alert || signal.description}</p>
        </div>
      )}

      <div className="mt-4 pl-4">
        <div className="relative h-2 rounded-full bg-gray-100">
          <div
            className={`absolute top-0 h-full rounded-full ${barColor}`}
            style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
          />
        </div>
        <div className="mt-1.5 flex justify-between text-[10px] text-gray-400 font-medium">
          {ticks.map((h) => (
            <span key={h}>{fmtHour(h)}</span>
          ))}
        </div>
        <p className="mt-1 text-xs text-gray-500 font-medium">{timeLabel}</p>
      </div>
    </div>
  );
}
