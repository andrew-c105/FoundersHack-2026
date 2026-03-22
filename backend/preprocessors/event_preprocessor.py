"""
Event preprocessor with LLM relevance filtering.

Pipeline: Raw events → LLM relevance filter → distance/capacity scoring → processed signals.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from llm.relevance_filter import get_crowd_confidence_modifier, llm_relevance_filter
from preprocessors.common import clamp, format_forecast_dt, haversine_km, parse_dt

SPORT_DURATION_HOURS = {
    "AFL": 2.5,
    "NRL": 2.0,
    "A-League": 2.0,
    "Cricket": 8.0,
    "concert": 2.0,
    "festival": 6.0,
    "default": 2.0,
}


def _get_affected_hours(event_datetime: datetime, event_type: str) -> list[datetime]:
    """Return list of hour-level datetimes the event impacts (including dispersal)."""
    duration = SPORT_DURATION_HOURS.get(event_type, 2.0)
    end_dt = event_datetime + timedelta(hours=duration)
    dispersal_end = end_dt + timedelta(hours=1)
    affected: list[datetime] = []
    current = event_datetime
    while current <= dispersal_end:
        affected.append(current)
        current += timedelta(hours=1)
    return affected


def process_event_signal(
    raw_json: dict[str, Any],
    location_id: str,
    business_profile: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """
    Process event signals with LLM relevance scoring.

    If business_profile is provided, runs the LLM relevance filter first.
    Otherwise falls back to the original distance+capacity-only logic.
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

    if not events:
        return []

    now = datetime.now(timezone.utc)

    # ── Step 1: LLM relevance filter ─────────────────────────────
    scored_lookup: dict[str, dict[str, Any]] = {}
    if business_profile:
        scored_events = llm_relevance_filter(events, business_profile, location_id)
        for se in scored_events:
            scored_lookup[se.get("event_name", "")] = se
    # If no business_profile, skip LLM and process all events (backward compat)

    out: list[dict[str, Any]] = []

    for ev in events:
        name = ev.get("name") or ev.get("title") or "Event"

        # ── Step 2: Check LLM verdict (if available) ─────────────
        scored = scored_lookup.get(name)
        if scored is not None and not scored.get("include", True):
            # LLM said exclude this event
            continue

        relevance_score = scored.get("relevance_score", 0.5) if scored else 0.5
        crowd_type = scored.get("crowd_type", "mixed") if scored else "mixed"

        # ── Step 3: Distance and capacity (unchanged core logic) ─
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

        walk_minutes = float(ev.get("walk_minutes", 15))
        transit_minutes = float(ev.get("transit_minutes", 15))

        proximity_score = max(0.0, 1.0 - (walk_minutes / 30.0))
        capacity_score = min(capacity / 50000.0, 1.0)
        raw_uplift = proximity_score * capacity_score * 0.45

        # ── Step 4: Scale uplift by LLM relevance score ──────────
        adjusted_uplift = raw_uplift * relevance_score

        # ── Step 5: Base confidence from signal quality ──────────
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

        # ── Step 6: Multiply confidence by crowd type modifier ───
        crowd_modifier = get_crowd_confidence_modifier(crowd_type, transit_minutes)
        confidence = clamp(base_conf * crowd_modifier, 0.10, 0.99)

        # ── Step 7: Determine affected hours ─────────────────────
        if end is None:
            end = start + timedelta(hours=3)

        event_type = ev.get("event_type") or ev.get("competition") or "default"
        affected_hours = _get_affected_hours(start, event_type)

        # ── Step 8: One result per affected hour ─────────────────
        for hour_dt in affected_hours:
            if hour_dt < now - timedelta(days=1):
                continue
            if adjusted_uplift < 1e-6:
                continue
            out.append(
                {
                    "location_id": location_id,
                    "signal_type": source,
                    "forecast_dt": format_forecast_dt(hour_dt),
                    "uplift_pct": round(adjusted_uplift, 4),
                    "signal_conf": round(confidence, 2),
                    "label": name,
                    "distance_km": round((walk_minutes * 80) / 1000, 2),  # roughly approx dist from walk
                    "source_url": source_url,
                }
            )

    return out
