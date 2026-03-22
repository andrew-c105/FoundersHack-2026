import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import Grainient from "../components/ui/Grainient";
import SignUpBlock from "../components/SignUpBlock";
import GradientText from "../components/GradientText";

export default function Landing() {
  const [showModal, setShowModal] = useState(false);
  const navigate = useNavigate();

  const isAuth = !!localStorage.getItem("locationId") || !!localStorage.getItem("auth");

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
          <img
            src="/peakly_logo.png"
            alt="Peakly"
            className="h-8 w-8 shrink-0 object-cover rounded-full mix-blend-multiply"
          />
          Peakly
        </div>
      </header>

      <div className="mx-auto max-w-5xl px-4 py-24 sm:py-32">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="text-center">
          <p className="text-lg sm:text-xl font-semibold uppercase text-blue-600 mb-6">Peakly</p>
          <h1 className="mx-auto max-w-4xl text-5xl font-extrabold tracking-tight text-gray-900 sm:text-6xl md:text-7xl">
            Hourly demand you can staff against —{" "}
            <GradientText
              colors={["#5227FF"]}
              animationSpeed={8}
              showBorder={false}
            >
              without sharing sales data.
            </GradientText>
          </h1>
          <p className="mx-auto mt-8 max-w-2xl text-lg leading-relaxed font-medium text-[#1a1a2e]">
            We fuse weather, events, transport, holidays, and local competition into a relative busyness index
            and a 30-day hourly forecast.
          </p>
          <div className="mt-12 flex flex-wrap justify-center gap-4">
              <button
                onClick={() => {
                  if (isAuth) {
                    navigate("/today");
                  } else {
                    setShowModal(true);
                  }
                }}
                className="rounded-xl bg-gray-900 px-8 py-4 font-semibold text-white shadow-lg shadow-gray-900/20 transition hover:bg-black hover:-translate-y-0.5"
              >
                Start Onboarding
              </button>
          </div>
        </motion.div>

        <AnimatePresence>
          {showModal && !isAuth && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm"
              onClick={(e) => {
                if (e.target === e.currentTarget) setShowModal(false);
              }}
            >
              <div className="relative w-full max-w-sm">
                <button
                  className="absolute -right-3 -top-3 z-10 flex h-8 w-8 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-500 shadow-sm transition hover:text-gray-900"
                  onClick={() => setShowModal(false)}
                >
                  ×
                </button>
                <SignUpBlock
                  onClose={() => setShowModal(false)}
                  onSuccess={() => {
                    setShowModal(false);
                    navigate("/onboarding");
                  }}
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
