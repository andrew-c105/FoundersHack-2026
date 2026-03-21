from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import database as db
from preprocessors.common import format_forecast_dt, haversine_km


def _parse_trading_hours(trading_json: str | None) -> list[tuple[int, int]]:
    """Returns list of (day 0-6, hour) open hours for next 7 days — default cafe hours."""
    default = []
    for d in range(7):
        for h in range(7, 22):
            default.append((d, h))
    if not trading_json:
        return default
    try:
        import json

        data = json.loads(trading_json)
        hours_map = data.get("hours") or data
        out: list[tuple[int, int]] = []
        for d in range(7):
            key = str(d)
            rng = hours_map.get(key) or hours_map.get(d)
            if not rng:
                continue
            open_h, close_h = int(rng[0]), int(rng[1])
            for h in range(open_h, close_h):
                out.append((d, h))
        return out or default
    except Exception:
        return default


def process_competitor_signal(raw_json: dict[str, Any], location_id: str) -> list[dict[str, Any]]:
    """
    Google Places nearby search style: { results: [ { place_id, name, business_status, rating, ... geometry } ], location: {lat,lng} }
    """
    loc = raw_json.get("location") or {}
    biz_lat = float(loc.get("lat", -33.8688))
    biz_lng = float(loc.get("lng", 151.2093))
    results = raw_json.get("results") or raw_json.get("places") or []
    if not results and raw_json.get("place_id"):
        results = [raw_json]

    location_row = db.get_location(location_id)
    trading = location_row.get("trading_hours_json") if location_row else None
    trading_slots = _parse_trading_hours(trading)

    tracking = db.get_competitor_tracking(location_id)
    now = datetime.now(timezone.utc)

    total_uplift_by_slot: dict[tuple[int, int], float] = {}
    confidences: list[float] = []

    for place in results:
        geom = place.get("geometry") or {}
        locg = geom.get("location") or {}
        plat = float(locg.get("lat", biz_lat))
        plng = float(locg.get("lng", biz_lng))
        dist = haversine_km(biz_lat, biz_lng, plat, plng)
        if dist > 1.5:
            continue

        status = str(place.get("business_status") or "OPERATIONAL").upper()
        pid = place.get("place_id") or place.get("id") or place.get("name", "unknown")
        confirmed = status in ("OPERATIONAL", "CLOSED_TEMPORARILY", "PERMANENTLY_CLOSED")

        if status == "PERMANENTLY_CLOSED":
            key = str(pid)
            if key not in tracking:
                tracking[key] = now.isoformat()
            try:
                first = datetime.fromisoformat(tracking[key].replace("Z", "+00:00"))
            except ValueError:
                first = now
            if first.tzinfo is None:
                first = first.replace(tzinfo=timezone.utc)
            days_since = (now - first).days
            recency = max(0.0, 1.0 - (days_since / 90.0))
            piece = 0.09 * recency * (1 - dist / 1.5)
            confidences.append(0.88 if confirmed else 0.55)
            for d, h in trading_slots:
                total_uplift_by_slot[(d, h)] = total_uplift_by_slot.get((d, h), 0.0) + piece
        else:
            confidences.append(0.88 if confirmed else 0.55)

    db.update_location_tracking(location_id, tracking)

    avg_conf = sum(confidences) / len(confidences) if confidences else 0.55

    out: list[dict[str, Any]] = []
    start_day = now.weekday()
    for day_offset in range(7):
        base = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=day_offset)
        dow = base.weekday()
        for h in range(24):
            if (dow, h) not in trading_slots:
                continue
            uplift = total_uplift_by_slot.get((dow, h), 0.0)
            if uplift <= 0:
                continue
            slot_dt = base.replace(hour=h)
            out.append(
                {
                    "location_id": location_id,
                    "signal_type": "google_places",
                    "forecast_dt": format_forecast_dt(slot_dt),
                    "uplift_pct": uplift,
                    "confidence": avg_conf,
                    "label": "Nearby competitor permanently closed",
                    "distance_km": None,
                    "source_url": "https://maps.google.com/",
                }
            )

    return out
