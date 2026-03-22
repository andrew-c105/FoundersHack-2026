import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

export default function SettingsPage() {
  const id = localStorage.getItem("locationId")!;
  const [loc, setLoc] = useState<Record<string, unknown> | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    const l = await api.getLocation(id);
    setLoc(l);
  }

  useEffect(() => {
    load().catch(() => setLoc(null));
  }, [id]);

  async function refresh() {
    setBusy(true);
    setMsg(null);
    try {
      await api.refresh(id);
      setMsg("Signals refreshed manually.");
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : "Error");
    } finally {
      setBusy(false);
    }
  }

  // Determine an initial toggle state just for UI
  const [toggles, setToggles] = useState<Record<string, boolean>>({
    events: true,
    weather: true,
    competitors: true,
    traffic: true,
    school: true,
    sports: true,
  });

  const toggleHandler = (key: string) => {
    setToggles(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const navigate = useNavigate();

  if (!loc) return <p className="text-gray-500">Loading…</p>;

  return (
    <div className="max-w-4xl space-y-6 pb-20">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-2xl font-bold text-gray-900">Settings</h1>
        <div className="flex gap-3">
          <button
            onClick={refresh}
            disabled={busy}
            className="rounded-lg bg-white border border-gray-200 shadow-sm px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition disabled:opacity-50"
          >
            {busy ? "Refreshing..." : "Force refresh signals"}
          </button>
          <button
            onClick={() => {
              localStorage.removeItem("auth");
              localStorage.removeItem("locationId");
              navigate("/");
            }}
            className="rounded-lg bg-white border border-gray-200 shadow-sm px-4 py-2 text-sm font-medium text-gray-500 hover:bg-gray-100 hover:text-gray-900 transition"
          >
            Logout
          </button>
        </div>
      </div>

      {msg && (
        <div className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm font-medium text-blue-600">
          {msg}
        </div>
      )}

      {/* Business Profile */}
      <div className="rounded-2xl border border-gray-100 bg-white shadow-sm p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-6">Business profile</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Business location</label>
            <input
              type="text"
              defaultValue={String(loc.address || "McDonald's Circular Quay")}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Business type</label>
            <select
              defaultValue={String(loc.business_type).replace("_", " ")}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 capitalize"
            >
              <option>{String(loc.business_type).replace("_", " ")}</option>
              <option>Fast food / QSR</option>
              <option>Retail clothing</option>
              <option>Supermarket</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Seating capacity</label>
            <input
              type="number"
              defaultValue={48}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Avg transaction ($)</label>
            <input
              type="number"
              defaultValue={14}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Signal Sources */}
      <div className="rounded-2xl border border-gray-100 bg-white shadow-sm p-6">
        <div className="mb-6">
          <h2 className="text-lg font-bold text-gray-900">Signal sources</h2>
          <p className="mt-1 text-sm text-gray-500">Turn off signals that aren't relevant to your location</p>
        </div>
        <div className="divide-y divide-gray-100 border-t border-gray-100">
          {[
            { key: "events", title: "Local events", subtitle: "Council Events + Eventbrite within 3km" },
            { key: "weather", title: "Weather", subtitle: "Open-Meteo 7-day forecast" },
            { key: "competitors", title: "Competitor closures", subtitle: "Google Places status monitoring" },
            { key: "traffic", title: "Road closures", subtitle: "Live Traffic NSW" },
            { key: "school", title: "School holidays", subtitle: "NSW term dates calendar" },
            { key: "sports", title: "Sport Fixtures (AFL/NFL/A-League)", subtitle: "Seasonal fixture calendar" }
          ].map((item) => {
            const isActive = toggles[item.key];
            return (
              <div key={item.key} className="flex items-center justify-between py-4">
                <div>
                  <h3 className="text-sm font-semibold text-gray-900">{item.title}</h3>
                  <p className="mt-0.5 text-sm text-gray-500">{item.subtitle}</p>
                </div>
                <button
                  type="button"
                  onClick={() => toggleHandler(item.key)}
                  className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${isActive ? "bg-blue-600" : "bg-gray-200"
                    }`}
                >
                  <span
                    className={`inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${isActive ? "translate-x-5" : "translate-x-0"
                      }`}
                  />
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* POS Data */}
      <div className="rounded-2xl border border-gray-100 bg-white shadow-sm p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-6">POS data</h2>
        <div className="divide-y divide-gray-100 border-t border-gray-100">
          <div className="flex items-center justify-between py-4">
            <div>
              <h3 className="text-sm font-semibold text-gray-900">Last upload</h3>
              <p className="mt-0.5 text-sm text-gray-500">pos_history_march.csv — 14 Mar 2026</p>
            </div>
            <span className="rounded-full bg-green-50 px-3 py-1 text-xs font-semibold text-green-700">Connected</span>
          </div>
          <div className="flex items-center justify-between py-4">
            <div>
              <h3 className="text-sm font-semibold text-gray-900">Model trained on</h3>
              <p className="mt-0.5 text-sm text-gray-500">52 weeks of hourly data</p>
            </div>
            <span className="rounded-full bg-green-50 px-3 py-1 text-xs font-semibold text-green-700">Up to date</span>
          </div>
          <div className="flex items-center justify-between pt-4">
            <div>
              <h3 className="text-sm font-semibold text-gray-900">Auto-sync</h3>
              <p className="mt-0.5 text-sm text-gray-500">Upload new CSV weekly to improve accuracy</p>
            </div>
            <button className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 transition">
              Upload new data
            </button>
          </div>
        </div>
      </div>

      {/* Forecast Accuracy */}
      <div className="rounded-2xl border border-gray-100 bg-white shadow-sm p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-6">Forecast accuracy — last 30 days</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="rounded-xl border border-gray-100 bg-gray-50 flex flex-col items-center justify-center p-6 text-center">
            <div className="text-3xl font-black text-green-600">91%</div>
            <div className="text-sm font-medium text-gray-500 mt-2">within 10% accuracy</div>
          </div>
          <div className="rounded-xl border border-gray-100 bg-gray-50 flex flex-col items-center justify-center p-6 text-center">
            <div className="text-3xl font-black text-gray-900">847</div>
            <div className="text-sm font-medium text-gray-500 mt-2">hourly predictions made</div>
          </div>
          <div className="rounded-xl border border-gray-100 bg-gray-50 flex flex-col items-center justify-center p-6 text-center">
            <div className="text-3xl font-black text-green-600">+$1,240</div>
            <div className="text-sm font-medium text-gray-500 mt-2">est. labour savings</div>
          </div>
        </div>
      </div>
    </div>
  );
}
