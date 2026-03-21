import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";

const nav = [
  { to: "/today", label: "Today's brief" },
  { to: "/forecast", label: "Monthly forecast" },
  { to: "/accuracy", label: "Accuracy" },
  { to: "/settings", label: "Settings" },
];

export default function Layout() {
  const navigate = useNavigate();
  const locId = localStorage.getItem("locationId");
  if (!locId) {
    navigate("/onboarding");
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-3">
          <button
            type="button"
            onClick={() => navigate("/today")}
            className="font-display text-lg font-semibold tracking-tight text-cyan-300"
          >
            OpsForecast
          </button>
          <nav className="flex flex-wrap gap-1 text-sm">
            {nav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-1.5 transition-colors ${
                    isActive ? "bg-cyan-500/20 text-cyan-200" : "text-slate-400 hover:text-white"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <motion.main
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        className="mx-auto max-w-6xl px-4 py-8"
      >
        <Outlet />
      </motion.main>
    </div>
  );
}
