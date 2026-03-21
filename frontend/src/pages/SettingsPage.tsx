import { useEffect, useState } from "react";
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
      setMsg("Signals refreshed.");
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : "Error");
    } finally {
      setBusy(false);
    }
  }

  async function retrain() {
    setBusy(true);
    setMsg(null);
    try {
      await api.bootstrap(id);
      setMsg("Model retrained and predictions updated.");
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : "Error");
    } finally {
      setBusy(false);
    }
  }

  if (!loc) return <p className="text-slate-400">Loading…</p>;

  return (
    <div className="max-w-xl space-y-6">
      <h1 className="font-display text-2xl font-bold text-white">Location settings</h1>
      <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-sm text-slate-300">
        <p>
          <span className="text-slate-500">ID</span> {String(loc.id)}
        </p>
        <p className="mt-2">
          <span className="text-slate-500">Type</span> {String(loc.business_type)}
        </p>
        <p className="mt-2">
          <span className="text-slate-500">Address</span> {String(loc.address || "—")}
        </p>
      </div>
      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          disabled={busy}
          onClick={refresh}
          className="rounded-xl bg-slate-800 px-4 py-2 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
        >
          Refresh live signals
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={retrain}
          className="rounded-xl bg-cyan-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
        >
          Retrain + predict
        </button>
      </div>
      {msg && <p className="text-sm text-cyan-300">{msg}</p>}
      <p className="text-xs text-slate-500">
        Toggle API keys in backend <code className="text-slate-400">.env</code> (never commit secrets).
      </p>
    </div>
  );
}
