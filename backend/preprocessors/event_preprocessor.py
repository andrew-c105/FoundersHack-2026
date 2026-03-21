from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from preprocessors.common import clamp, format_forecast_dt, haversine_km, parse_dt


def process_event_signal(raw_json: dict[str, Any], location_id: str) -> list[dict[str, Any]]:
    """
    Ticketmaster + Eventbrite shaped payloads:
    raw_json may be a single event or { "events": [...], "source": "eventbrite"|"ticketmaster", "location": {lat,lng} }
    """
    loc = raw_json.get("location") or {}
    biz_lat = float(loc.get("lat", raw_json.get("biz_lat", -33.8688)))
    biz_lng = float(loc.get("lng", raw_json.get("biz_lng", 151.2093)))
    source = raw_json.get("source", "ticketmaster")
    if source not in ("ticketmaster", "eventbrite"):
        source = "ticketmaster"

    events = raw_json.get("events")
    if events is None:
        events = [raw_json] if raw_json.get("name") or raw_json.get("event_start_datetime") else []

    out: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for ev in events:
        name = ev.get("name") or ev.get("title") or "Event"
        vlat = float(ev.get("venue_lat", ev.get("latitude", biz_lat)))
        vlng = float(ev.get("venue_lng", ev.get("longitude", biz_lng)))
        capacity = float(ev.get("capacity") or 5000)
        tickets_sold = float(ev.get("tickets_sold") or 0)
        status = str(ev.get("status") or "announced").lower()
        start = parse_dt(ev.get("event_start_datetime") or ev.get("start") or ev.get("start_utc"))
        end = parse_dt(ev.get("event_end_time") or ev.get("end"))
        source_url = ev.get("source_url") or ev.get("url") or ""

        if start is None:
            continue

        dist = haversine_km(biz_lat, biz_lng, vlat, vlng)
        if dist > 3.0:
            continue

        proximity_score = 1 - (dist / 3.0)
        capacity_score = min(capacity / 50000.0, 1.0)
        base_uplift = proximity_score * capacity_score * 0.45

        base_conf = 0.5
        if status == "onsale":
            base_conf += 0.25
        elif status == "announced":
            base_conf += 0.10
        elif status == "unconfirmed":
            base_conf -= 0.20
        if tickets_sold > 10000:
            base_conf += 0.15
        if tickets_sold == 0:
            base_conf -= 0.10
        days_until = (start.date() - now.date()).days
        if days_until <= 2:
            base_conf += 0.10
        if days_until >= 6:
            base_conf -= 0.15
        confidence = clamp(base_conf, 0.10, 0.99)

        if end is None:
            end = start + timedelta(hours=3)

        end_hour = end.replace(minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        peak_uplift = base_uplift
        for i, mult in enumerate([1.0, 0.5, 0.25]):
            hr = end_hour + timedelta(hours=i)
            if hr < now - timedelta(days=1):
                continue
            uplift = peak_uplift * mult
            if uplift < 1e-6:
                continue
            out.append(
                {
                    "location_id": location_id,
                    "signal_type": source,
                    "forecast_dt": format_forecast_dt(hr),
                    "uplift_pct": uplift,
                    "confidence": confidence,
                    "label": name,
                    "distance_km": round(dist, 2),
                    "source_url": source_url,
                }
            )

    return out
