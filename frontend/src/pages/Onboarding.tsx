import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../api";

const types = ["fast_food", "dine_in", "cafe", "bubble_tea", "retail"] as const;

const defaultHours = Object.fromEntries(
  Array.from({ length: 7 }, (_, d) => [String(d), [9, 21]])
) as Record<string, number[]>;

export default function Onboarding() {
  const nav = useNavigate();
  const [step, setStep] = useState(0);
  const [businessType, setBusinessType] = useState<string>("cafe");
  const [address, setAddress] = useState("1 George St, Sydney NSW");
  const [maxStaff, setMaxStaff] = useState(6);
  const [hours] = useState({ hours: defaultHours });
  const [toggles, setToggles] = useState<Record<string, boolean>>({
    open_meteo: true,
    eventbrite: true,
    google_places: true,
    transport_nsw: true,
    live_traffic: true,
    static: true,
  });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function finish() {
    setLoading(true);
    setErr(null);
    try {
      const { location_id } = await api.onboarding({
        business_type: businessType,
        address,
        max_staff: maxStaff,
        trading_hours: hours,
        signal_toggles: toggles,
      });
      await api.bootstrap(location_id);
      localStorage.setItem("locationId", location_id);
      nav("/today");
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 px-4 py-12 text-slate-100">
      <div className="mx-auto max-w-lg">
        <h1 className="font-display text-2xl font-bold text-white">Onboarding</h1>
        <p className="mt-1 text-sm text-slate-400">Step {step + 1} of 4</p>
        <div className="mt-2 h-1 overflow-hidden rounded-full bg-slate-800">
          <motion.div
            className="h-full bg-cyan-500"
            animate={{ width: `${((step + 1) / 4) * 100}%` }}
          />
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="mt-10 space-y-4"
          >
            {step === 0 && (
              <>
                <p className="text-slate-300">Choose business type</p>
                <div className="grid gap-2">
                  {types.map((t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => setBusinessType(t)}
                      className={`rounded-xl border px-4 py-3 text-left text-sm capitalize ${
                        businessType === t
                          ? "border-cyan-500 bg-cyan-500/10 text-cyan-100"
                          : "border-slate-700 hover:border-slate-500"
                      }`}
                    >
                      {t.replace("_", " ")}
                    </button>
                  ))}
                </div>
              </>
            )}
            {step === 1 && (
              <>
                <label className="block text-slate-300">Address</label>
                <input
                  className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-white outline-none focus:border-cyan-500"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                />
                <p className="text-xs text-slate-500">Used for geocode, signals, and Popular Times baseline.</p>
              </>
            )}
            {step === 2 && (
              <>
                <label className="block text-slate-300">Max staff (ceiling for recommendations)</label>
                <input
                  type="number"
                  min={1}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-white"
                  value={maxStaff}
                  onChange={(e) => setMaxStaff(Number(e.target.value))}
                />
                <p className="text-xs text-slate-500">Default trading hours 9–21 every day (editable later).</p>
              </>
            )}
            {step === 3 && (
              <>
                <p className="text-slate-300">Signal sources</p>
                {Object.keys(toggles).map((k) => (
                  <label key={k} className="flex items-center justify-between rounded-xl border border-slate-800 px-4 py-2">
                    <span className="capitalize text-sm text-slate-200">{k.replace("_", " ")}</span>
                    <input
                      type="checkbox"
                      checked={toggles[k]}
                      onChange={(e) => setToggles({ ...toggles, [k]: e.target.checked })}
                    />
                  </label>
                ))}
              </>
            )}
          </motion.div>
        </AnimatePresence>

        {err && <p className="mt-4 text-sm text-red-400">{err}</p>}

        <div className="mt-10 flex justify-between gap-4">
          <button
            type="button"
            disabled={step === 0}
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            className="rounded-xl border border-slate-600 px-4 py-2 text-sm disabled:opacity-30"
          >
            Back
          </button>
          {step < 3 ? (
            <button
              type="button"
              onClick={() => setStep((s) => s + 1)}
              className="rounded-xl bg-cyan-600 px-5 py-2 text-sm font-semibold text-white"
            >
              Next
            </button>
          ) : (
            <button
              type="button"
              disabled={loading}
              onClick={finish}
              className="rounded-xl bg-cyan-500 px-5 py-2 text-sm font-semibold text-slate-950 disabled:opacity-50"
            >
              {loading ? "Setting up…" : "Finish & train model"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
