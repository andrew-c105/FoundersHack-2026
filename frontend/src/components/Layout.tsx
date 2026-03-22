import { useEffect } from "react";
import { Outlet, NavLink, useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";

const nav = [
  { to: "/today", label: "Dashboard", defaultIcon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" },
  { to: "/accuracy", label: "Accuracy", defaultIcon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" },
  { to: "/settings", label: "Settings", defaultIcon: "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" },
];

export default function Layout() {
  const navigate = useNavigate();
  const locId = localStorage.getItem("locationId");

  useEffect(() => {
    if (!locId) {
      navigate("/onboarding");
    }
  }, [locId, navigate]);

  if (!locId) {
    return null;
  }

  return (
    <div className="flex min-h-screen bg-[#f3f4f6] font-sans text-gray-900">
      {/* Sidebar */}
      <aside className="fixed inset-y-0 left-0 w-64 border-r border-gray-200 bg-white">
        <div className="flex h-16 items-center px-6 border-b border-gray-100">
          <Link to="/" className="group flex items-center gap-2 text-xl font-bold tracking-tight text-gray-900 transition-colors hover:text-blue-600 relative">
            <img
              src="/swell_logo.png"
              alt="Swell"
              className="h-8 w-8 shrink-0 object-contain transition-opacity group-hover:opacity-90"
            />
            Swell
            
            <span className="absolute left-1/2 top-full mt-2 -translate-x-1/2 whitespace-nowrap rounded-md bg-gray-800 px-2 py-1 text-xs font-medium text-white opacity-0 transition-opacity group-hover:opacity-100 pointer-events-none z-50">
              Back to home
              <svg className="absolute bottom-full left-1/2 -ml-1 h-2 w-2 text-gray-800" fill="currentColor" viewBox="0 0 8 8"><path d="M4 0l4 8H0z"/></svg>
            </span>
            <svg className="ml-1 h-4 w-4 text-gray-400 opacity-0 transition-all group-hover:opacity-100 group-hover:translate-x-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
          </Link>
        </div>
        
        <div className="px-4 py-6">
          <p className="px-2 text-xs font-semibold text-gray-400 uppercase tracking-widest mb-4">Main Menu</p>
          <nav className="space-y-1">
            {nav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${
                    isActive 
                      ? "bg-blue-50 text-blue-600" 
                      : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                  }`
                }
              >
                <svg className="h-5 w-5 opacity-75" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  {item.to === "/settings" && <path strokeLinecap="round" strokeLinejoin="round" d={item.defaultIcon} />}
                  {item.to === "/accuracy" && <path strokeLinecap="round" strokeLinejoin="round" d={item.defaultIcon} />}
                  {item.to === "/today" && <path strokeLinecap="round" strokeLinejoin="round" d={item.defaultIcon} />}
                </svg>
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="pl-64 flex-1 flex flex-col min-h-screen">
        {/* Top Header */}
        <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-8 sticky top-0 z-50">
          <div className="flex items-center text-sm text-gray-500 font-medium">
            Swell <span className="mx-2 text-gray-300">›</span> <span className="text-gray-900">Workspace</span>
          </div>

          <div className="flex items-center gap-6">
            {/* Feedback Button */}
            <button 
              className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-1.5 text-xs font-bold text-white shadow-md transition hover:bg-blue-700 hover:-translate-y-0.5"
              onClick={() => alert("Feedback system coming soon!")}
            >
              <svg className="h-4 w-4 text-yellow-300 fill-current" viewBox="0 0 24 24">
                <path d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Feedback
            </button>
            
            {/* User Profile Mock */}
            <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white text-sm font-medium shadow-sm cursor-pointer">
              L
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-8">
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
            className="mx-auto max-w-5xl"
          >
            <Outlet />
          </motion.div>
        </main>
      </div>
    </div>
  );
}
