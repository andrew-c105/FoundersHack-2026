import { Link } from "react-router-dom";
import { motion } from "framer-motion";

export default function Landing() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-cyan-950/40 text-slate-100">
      <div className="mx-auto max-w-5xl px-4 py-20">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-400/90">Franchise operations</p>
          <h1 className="mt-4 font-display text-4xl font-bold leading-tight text-white sm:text-5xl">
            Hourly demand you can staff against — without sharing sales data.
          </h1>
          <p className="mt-6 max-w-2xl text-lg text-slate-300">
            We fuse weather, events, transport, holidays, and local competition into a relative busyness index
            and a 30-day hourly forecast. One address and business type at signup.
          </p>
          <div className="mt-10 flex flex-wrap gap-4">
            <Link
              to="/onboarding"
              className="rounded-xl bg-cyan-500 px-6 py-3 font-semibold text-slate-950 shadow-lg shadow-cyan-500/25 transition hover:bg-cyan-400"
            >
              Start onboarding
            </Link>
            <a
              href="/docs"
              className="rounded-xl border border-slate-600 px-6 py-3 font-medium text-slate-200 hover:border-cyan-500/50"
              onClick={(e) => {
                e.preventDefault();
              }}
            >
              API docs (run backend)
            </a>
          </div>
        </motion.div>

        <div className="mt-24 grid gap-6 sm:grid-cols-3">
          {[
            { t: "External signals", d: "Weather, events, closures, PT, roadworks — stored raw, then scored." },
            { t: "Relative index", d: "Percent vs your normal Tuesday 7pm — works for QSR or boutique retail." },
            { t: "XGBoost + brief", d: "Model learns signal curves; Gemini turns peaks into manager language." },
          ].map((c, i) => (
            <motion.div
              key={c.t}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 * i }}
              className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6"
            >
              <h3 className="font-display text-lg font-semibold text-cyan-200">{c.t}</h3>
              <p className="mt-2 text-sm text-slate-400">{c.d}</p>
            </motion.div>
          ))}
        </div>

        <div className="mt-16 rounded-2xl border border-slate-800 bg-slate-900/30 p-8">
          <h2 className="font-display text-xl font-semibold text-white">Vs. typical BI tools</h2>
          <p className="mt-2 text-slate-400">
            No POS integration required for the demo path. Popular Times baseline + live APIs give you a credible
            story for judges; swap in your telemetry when you are ready.
          </p>
        </div>
      </div>
    </div>
  );
}
