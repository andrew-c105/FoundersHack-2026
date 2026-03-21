from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from preprocessors.common import format_forecast_dt, haversine_km, parse_dt


def _incident_point(incident: dict[str, Any]) -> tuple[float, float] | None:
    g = incident.get("geometry") or incident.get("Geometry") or {}
    if "lat" in incident and "lng" in incident:
        return float(incident["lat"]), float(incident["lng"])
    if "coordinates" in g:
        c = g["coordinates"]
        if isinstance(c[0], (list, tuple)):
            return float(c[1]), float(c[0])
        return float(c[1]), float(c[0])
    loc = incident.get("location") or {}
    if "latitude" in loc:
        return float(loc["latitude"]), float(loc["longitude"])
    return None


def process_transport_signal(raw_json: dict[str, Any], location_id: str) -> list[dict[str, Any]]:
    """
    Transport NSW + Live Traffic: { incidents: [ { incident_type, severity, start_time, end_time, geometry, ... } ], location: {lat,lng} }
    Or GTFS-style wrapper in raw_json['incidents'].
    """
    loc = raw_json.get("location") or {}
    biz_lat = float(loc.get("lat", -33.8688))
    biz_lng = float(loc.get("lng", 151.2093))
    incidents = raw_json.get("incidents") or raw_json.get("features") or []
    if not incidents and raw_json.get("incident_type"):
        incidents = [raw_json]

    stype = raw_json.get("signal_subtype") or "transport_nsw"
    if stype not in ("transport_nsw", "live_traffic"):
        stype = "transport_nsw"

    out: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for inc in incidents:
        itype = str(inc.get("incident_type") or inc.get("type") or "MINOR_WORKS").upper()
        pt = _incident_point(inc)
        if not pt:
            continue
        dist = haversine_km(biz_lat, biz_lng, pt[0], pt[1])
        if dist > 0.8:
            continue

        factor = 1 - dist / 0.8
        uplift = 0.0
        if itype in ("ROAD_CLOSURE", "MAJOR_WORKS"):
            uplift = -0.10 * factor
        elif itype == "MINOR_WORKS":
            uplift = -0.04 * factor

        confirmed = bool(inc.get("confirmed", True))
        confidence = 0.92 if confirmed else 0.65

        st = parse_dt(inc.get("start_time") or inc.get("start")) or now
        en = parse_dt(inc.get("end_time") or inc.get("end")) or (st + timedelta(hours=6))

        label = inc.get("roads_affected") or inc.get("title") or itype
        source_url = inc.get("source_url") or "https://opendata.transport.nsw.gov.au/"

        cur = st.replace(minute=0, second=0, microsecond=0)
        if cur.tzinfo is None:
            cur = cur.replace(tzinfo=timezone.utc)
        end_h = en.replace(minute=0, second=0, microsecond=0)
        if end_h.tzinfo is None:
            end_h = end_h.replace(tzinfo=timezone.utc)

        while cur <= end_h:
            out.append(
                {
                    "location_id": location_id,
                    "signal_type": stype,
                    "forecast_dt": format_forecast_dt(cur),
                    "uplift_pct": uplift,
                    "confidence": confidence,
                    "label": str(label)[:200],
                    "distance_km": round(dist, 3),
                    "source_url": source_url,
                }
            )
            cur += timedelta(hours=1)

    return out
