import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import Grainient from "../components/ui/Grainient";

export default function Landing() {
  return (
    <div className="relative min-h-screen text-gray-900 font-sans overflow-hidden">
      {/* Dynamic Background */}
      <div className="fixed inset-0 -z-10 w-full h-full">
        <Grainient
          color1="#ffffff"
          color2="#60a5fa" 
          color3="#1e40af"
          timeSpeed={0.25}
          colorBalance={0}
          warpStrength={1}
          warpFrequency={5}
          warpSpeed={2}
          warpAmplitude={50}
          blendAngle={0}
          blendSoftness={0.05}
          rotationAmount={500}
          noiseScale={2}
          grainAmount={0.1}
          grainScale={2}
          grainAnimated={false}
          contrast={1.5}
          gamma={1}
          saturation={1}
          centerX={0}
          centerY={0}
          zoom={0.9}
        />
      </div>
      {/* Super Simple Top Header for Landing */}
      <header className="h-16 px-6 sm:px-12 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xl font-bold tracking-tight text-gray-900 cursor-pointer">
            <div className="h-6 w-6 rounded-md bg-blue-600 flex items-center justify-center">
              <span className="text-white text-xs font-black">F</span>
            </div>
            FranchiseOps
        </div>
        <a href="/docs" className="text-sm font-medium text-gray-500 hover:text-gray-900">API Docs</a>
      </header>

      <div className="mx-auto max-w-5xl px-4 py-24 sm:py-32">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="text-center">
          <p className="text-sm font-semibold uppercase tracking-widest text-blue-600 mb-6">Franchise Operations</p>
          <h1 className="mx-auto max-w-4xl text-5xl font-extrabold tracking-tight text-gray-900 sm:text-6xl md:text-7xl">
            Hourly demand you can staff against — <span className="text-blue-600">without sharing sales data.</span>
          </h1>
          <p className="mx-auto mt-8 max-w-2xl text-lg text-gray-500 leading-relaxed">
            We fuse weather, events, transport, holidays, and local competition into a relative busyness index
            and a 30-day hourly forecast. One address and business type at signup.
          </p>
          <div className="mt-12 flex flex-wrap justify-center gap-4">
            <Link
              to="/onboarding"
              className="rounded-xl bg-gray-900 px-8 py-4 font-semibold text-white shadow-lg shadow-gray-900/20 transition hover:bg-black hover:-translate-y-0.5"
            >
              Start onboarding
            </Link>
            <a
              href="/docs"
              className="rounded-xl border border-gray-200 bg-white px-8 py-4 font-medium text-gray-700 shadow-sm transition hover:bg-gray-50 hover:border-gray-300"
              onClick={(e) => {
                e.preventDefault();
              }}
            >
              API docs (run backend)
            </a>
          </div>
        </motion.div>

        <div className="mt-32 grid gap-8 sm:grid-cols-3">
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
              className="rounded-2xl border border-gray-100 bg-white p-8 shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] transition hover:shadow-md"
            >
              <div className="h-10 w-10 flex items-center justify-center rounded-xl bg-blue-50 text-blue-600 mb-4">
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-gray-900">{c.t}</h3>
              <p className="mt-3 text-base text-gray-500 leading-relaxed">{c.d}</p>
            </motion.div>
          ))}
        </div>

        <div className="mt-16 rounded-3xl bg-gray-900 p-10 text-center shadow-2xl shadow-gray-900/20 sm:p-14 mb-20">
          <h2 className="text-3xl font-extrabold text-white">Vs. typical BI tools</h2>
          <p className="mt-4 max-w-3xl mx-auto text-lg text-gray-400">
            No POS integration required for the demo path. Popular Times baseline + live APIs give you a credible
            story for judges; swap in your telemetry when you are ready.
          </p>
        </div>
      </div>
    </div>
  );
}
