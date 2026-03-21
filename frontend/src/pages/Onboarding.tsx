import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../api";

const CheckIcon = () => (
  <svg className="h-5 w-5 text-slate-800" viewBox="0 0 24 24" fill="currentColor">
    <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm5.707 7.707a1 1 0 00-1.414-1.414L11 13.586 8.707 11.293a1 1 0 00-1.414 1.414l3 3a1 1 0 001.414 0l4-4z" />
  </svg>
);

const SpinnerIcon = () => (
  <svg className="h-5 w-5 animate-spin text-blue-600" fill="none" viewBox="0 0 24 24">
    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
  </svg>
);

function LoadingItem({ label, done }: { label: string; done: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <span className="flex w-5 justify-center">
        {done ? <CheckIcon /> : <SpinnerIcon />}
      </span>
      <span className={done ? "font-medium text-gray-900" : "text-gray-500"}>
        {label}
      </span>
    </div>
  );
}

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
  const [loadingStep, setLoadingStep] = useState(0);
  const [err, setErr] = useState<string | null>(null);

  async function finish() {
    setLoading(true);
    setStep(4);
    setLoadingStep(0);
    setErr(null);
    try {
      setLoadingStep(1);
      const { location_id } = await api.onboarding({
        business_type: businessType,
        address,
        max_staff: maxStaff,
        trading_hours: hours,
        signal_toggles: toggles,
      });

      setLoadingStep(2);
      const boot = api.bootstrap(location_id);

      // Slower, more deliberate ticks to allow background work to complete
      const t1 = setTimeout(() => setLoadingStep(3), 4500);
      const t2 = setTimeout(() => setLoadingStep(4), 8500);

      await boot;
      clearTimeout(t1);
      clearTimeout(t2);

      setLoadingStep(5);
      localStorage.setItem("locationId", location_id);
      setTimeout(() => nav("/today"), 2000);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Failed");
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#f3f4f6] font-sans px-4 py-20 text-gray-900">
      <div className="mx-auto max-w-lg">
        <h1 className="text-3xl font-extrabold tracking-tight text-gray-900">Get Started</h1>
        <p className="mt-2 text-sm font-medium text-gray-500">Step {Math.min(step + 1, 4)} of 4</p>
        <div className="mt-3 h-2 overflow-hidden rounded-full bg-gray-200">
          <motion.div
            className="h-full rounded-full bg-blue-600"
            animate={{ width: `${(Math.min(step + 1, 4) / 4) * 100}%` }}
          />
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="mt-12 space-y-6"
          >
            {step === 0 && (
              <>
                <p className="text-lg font-semibold text-gray-900">Choose business type</p>
                <div className="grid gap-3">
                  {types.map((t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => setBusinessType(t)}
                      className={`rounded-xl border px-5 py-4 text-left font-medium capitalize shadow-sm transition-all ${businessType === t
                          ? "border-blue-600 bg-blue-50 text-blue-700 ring-1 ring-blue-600"
                          : "border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50"
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
                <label className="block text-lg font-semibold text-gray-900 mb-2">Address</label>
                <input
                  className="w-full rounded-xl border border-gray-300 bg-white px-5 py-4 text-gray-900 shadow-sm outline-none focus:border-blue-600 focus:ring-1 focus:ring-blue-600 transition"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                />
                <p className="mt-2 text-sm text-gray-500">Used for local signals and Popular Times baseline.</p>
              </>
            )}
            {step === 2 && (
              <>
                <label className="block text-lg font-semibold text-gray-900 mb-2">Max staff floor</label>
                <input
                  type="number"
                  min={1}
                  className="w-full rounded-xl border border-gray-300 bg-white px-5 py-4 text-gray-900 shadow-sm outline-none focus:border-blue-600 focus:ring-1 focus:ring-blue-600 transition"
                  value={maxStaff}
                  onChange={(e) => setMaxStaff(Number(e.target.value))}
                />
                <p className="mt-2 text-sm text-gray-500">Default trading hours 9–21 every day (editable later).</p>
              </>
            )}
            {step === 3 && (
              <>
                <p className="text-lg font-semibold text-gray-900 mb-4">Signal sources</p>
                <div className="space-y-3">
                  {Object.keys(toggles).map((k) => (
                    <label key={k} className="flex items-center justify-between rounded-xl border border-gray-200 bg-white shadow-sm px-5 py-4 cursor-pointer hover:bg-gray-50 transition">
                      <span className="capitalize font-medium text-gray-700">{k.replace("_", " ")}</span>
                      <input
                        type="checkbox"
                        checked={toggles[k]}
                        onChange={(e) => setToggles({ ...toggles, [k]: e.target.checked })}
                        className="h-5 w-5 rounded border-gray-300 text-blue-600 focus:ring-blue-600"
                      />
                    </label>
                  ))}
                </div>
              </>
            )}
            {step === 4 && (
              <div className="rounded-2xl border border-gray-100 bg-white p-8 shadow-sm">
                <p className="mb-6 text-xl font-bold text-gray-900">Initializing workspace...</p>
                <div className="space-y-4">
                  <LoadingItem label="Provisioning database tables" done={loadingStep > 0} />
                  <LoadingItem label="Connecting to signal sources" done={loadingStep > 1} />
                  <LoadingItem label="Ingesting historical baseline data" done={loadingStep > 2} />
                  <LoadingItem label="Training predictive model" done={loadingStep > 3} />
                  <LoadingItem label="Finalizing dashboard" done={loadingStep > 4} />
                </div>
              </div>
            )}
          </motion.div>
        </AnimatePresence>

        {err && <p className="mt-6 rounded-lg border border-red-100 bg-red-50 p-3 text-sm font-medium text-red-600">{err}</p>}

        {step < 4 && (
          <div className="mt-12 flex justify-between gap-4">
            <button
              type="button"
              onClick={() => step === 0 ? nav("/") : setStep((s) => Math.max(0, s - 1))}
              className="rounded-xl border border-gray-300 bg-white px-6 py-3 font-semibold text-gray-700 shadow-sm transition hover:bg-gray-50 disabled:opacity-40 disabled:hover:bg-white"
            >
              Back
            </button>
            {step < 3 ? (
              <button
                type="button"
                onClick={() => setStep((s) => s + 1)}
                className="rounded-xl bg-blue-600 px-8 py-3 font-semibold text-white shadow-sm transition hover:bg-blue-700 hover:-translate-y-0.5"
              >
                Next
              </button>
            ) : (
              <button
                type="button"
                disabled={loading}
                onClick={finish}
                className="rounded-xl bg-blue-600 px-8 py-3 font-semibold text-white shadow-sm transition hover:bg-blue-700 hover:-translate-y-0.5 disabled:opacity-50 disabled:hover:translate-y-0"
              >
                {loading ? "Setting up…" : "Finish"}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
