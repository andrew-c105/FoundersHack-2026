const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function j<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || r.statusText);
  }
  if (r.status === 204) return undefined as T;
  return r.json() as Promise<T>;
}

export const api = {
  health: () => j<{ status: string }>("/api/health"),
  onboarding: (body: Record<string, unknown>) =>
    j<{ location_id: string }>("/api/locations/onboarding", { method: "POST", body: JSON.stringify(body) }),
  listLocations: () => j<Record<string, unknown>[]>("/api/locations"),
  getLocation: (id: string) => j<Record<string, unknown>>(`/api/locations/${id}`),
  bootstrap: (id: string) =>
    j<{ mae: number; predictions: number }>(`/api/locations/${id}/bootstrap-model`, { method: "POST" }),
  refresh: (id: string) => j<{ status: string }>(`/api/locations/${id}/refresh`, { method: "POST" }),
  predictions: (id: string) => j<PredictionRow[]>(`/api/locations/${id}/predictions`),
  brief: (id: string, date?: string) => {
    const q = date ? `?date=${encodeURIComponent(date)}` : "";
    return j<BriefResponse>(`/api/locations/${id}/brief${q}`);
  },
  alerts: (id: string, threshold = 30) =>
    j<PredictionRow[]>(`/api/locations/${id}/alerts?threshold=${threshold}`),
  signalsHour: (id: string, forecastDt: string) =>
    j<SignalRow[]>(`/api/locations/${id}/signals/hour?forecast_dt=${encodeURIComponent(forecastDt)}`),
  signalsDay: (id: string, date: string) =>
    j<DaySignalsResponse>(`/api/locations/${id}/signals/day?date=${encodeURIComponent(date)}`),
  accuracy: (id: string) => j<{ history: { mae: number; evaluated_at: string }[] }>(`/api/locations/${id}/accuracy`),
  patchLocation: (id: string, body: Record<string, unknown>) =>
    j<Record<string, unknown>>(`/api/locations/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
};

export type PredictionRow = {
  forecast_dt: string;
  busyness_index: number;
  baseline_score: number;
  deviation_pct: number;
  confidence: number;
};

export type SignalRow = {
  signal_type: string;
  label: string | null;
  uplift_pct: number;
  confidence: number;
  distance_km: number | null;
};

export type DaySignal = {
  label: string;
  signal_type: string;
  uplift_pct: number;
  confidence: number;
  distance_km: number | null;
  source_url: string | null;
  start_hour: number;
  end_hour: number;
  description?: string;
  temp_low?: number;
  temp_high?: number;
  total_rain_mm?: number;
  conditions?: string;
  outlier?: boolean;
  outlier_hours?: string;
  outlier_label?: string;
};

export type DaySignalsResponse = {
  date: string;
  signals: DaySignal[];
  brief: string;
  positive_count: number;
  negative_count: number;
  total_signals: number;
};

export type BriefResponse = {
  date: string;
  brief: string;
  peak_hour: PredictionRow | null;
  hours: PredictionRow[];
};
