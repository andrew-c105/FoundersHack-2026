import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Landing from "./pages/Landing";
import Onboarding from "./pages/Onboarding";
import TodayBrief from "./pages/TodayBrief";
import MonthlyForecast from "./pages/MonthlyForecast";
import SignalMap from "./pages/SignalMap";
import SettingsPage from "./pages/SettingsPage";
import AccuracyPage from "./pages/AccuracyPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/onboarding" element={<Onboarding />} />
      <Route element={<Layout />}>
        <Route path="/today" element={<TodayBrief />} />
        <Route path="/forecast" element={<MonthlyForecast />} />
        <Route path="/map" element={<SignalMap />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/accuracy" element={<AccuracyPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
