import { useEffect, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import { api, type MapPayload } from "../api";

export default function SignalMap() {
  const id = localStorage.getItem("locationId")!;
  const [data, setData] = useState<MapPayload | null>(null);

  useEffect(() => {
    api.mapSignals(id).then(setData).catch(() => setData(null));
  }, [id]);

  if (!data) return <p className="text-slate-400">Loading map…</p>;

  const { center, markers } = data;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="font-display text-2xl font-bold text-white">Signal map</h1>
        <p className="text-sm text-slate-400">Overlays scaled by uplift; green positive, red negative.</p>
      </div>
      <div className="overflow-hidden rounded-2xl border border-slate-800">
        <MapContainer center={[center.lat, center.lng]} zoom={14} style={{ height: 440, width: "100%" }}>
          <TileLayer attribution="&copy; OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <CircleMarker
            center={[center.lat, center.lng]}
            radius={12}
            pathOptions={{ color: "#22d3ee", fillColor: "#22d3ee", fillOpacity: 0.25 }}
          >
            <Popup>Your location</Popup>
          </CircleMarker>
          {markers.map((m, i) => (
            <CircleMarker
              key={`${m.label}-${i}`}
              center={[m.lat, m.lng]}
              radius={8 + Math.min(40, Math.abs(m.uplift_pct) * 120)}
              pathOptions={{
                color: m.positive ? "#22c55e" : "#ef4444",
                fillColor: m.positive ? "#22c55e" : "#ef4444",
                fillOpacity: 0.35,
              }}
            >
              <Popup>
                <div className="text-slate-900">
                  <strong>{m.label || m.signal_type}</strong>
                  <div>Uplift: {(m.uplift_pct * 100).toFixed(1)}%</div>
                  <div>Confidence: {m.confidence}</div>
                </div>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
}
