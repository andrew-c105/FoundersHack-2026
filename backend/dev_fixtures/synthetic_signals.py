import os
import json
import logging
from datetime import datetime, time, timezone
from typing import Any
from zoneinfo import ZoneInfo

import database as db
from preprocessors.common import format_forecast_dt

logger = logging.getLogger(__name__)

_SYDNEY_TZ = ZoneInfo("Australia/Sydney")


def _sydney_to_utc(date_str: str, hour: int) -> str:
    """Convert a Sydney local date + hour to a UTC forecast_dt key."""
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    local = datetime.combine(d, time(hour, 0, 0), tzinfo=_SYDNEY_TZ)
    return format_forecast_dt(local.astimezone(timezone.utc))


def inject_synthetic_signals(location_id: str) -> None:
    print("[SYNTHETIC] Injecting synthetic signals for 2026-03-23 for development testing.")

    # We insert these into the processed_signals table directly so the ML pipeline 
    # and brief Generator treat them as real incoming inputs.
    
    signals = []

    # 1. Weather Signal
    # impact_direction: negative, impact_magnitude: 0.6, impact_conf: 0.85, low_temp: 18, high_temp: 22, rainfall_mm: 18, conditions: 'Heavy rain', uplift: -14, active_hours: '11:00-14:00', reasoning: 'Mostly overcast with morning showers clearing by early afternoon. Net negative effect on foot traffic, particularly lunch period.', outlier_alert: 'Heavy rain 11:00–14:00 — lunch period likely significantly impacted. Consider reducing lunch staffing.', hourly_pattern: negative all day with heaviest impact 11:00–14:00. This should render using the existing weather card component shown in the designs.
    signals.append({
        "location_id": location_id,
        "signal_type": "open_meteo",
        "forecast_date": "2026-03-23",
        "uplift_pct": -0.14,
        "signal_conf": 0.85,
        "label": "Weather Notice: Monday 23 Mar",
        "distance_km": None,
        "source_url": "synthetic",
        "description": "Heavy rain 11:00–14:00 — lunch period likely significantly impacted. Consider reducing lunch staffing.",
        "extra": {
            "low_temp": 18.0,
            "high_temp": 22.0,
            "temp_low": 18.0,
            "temp_high": 22.0,
            "rainfall_mm": 18.0,
            "total_rain_mm": 18.0,
            "conditions": "Heavy rain",
            "start_hour": 11,
            "end_hour": 14,
            "active_hours": "11:00-14:00",
            "outlier": True,
            "outlier_alert": "Heavy rain 11:00–14:00 — lunch period likely significantly impacted. Consider reducing lunch staffing.",
            "hourly_pattern": "negative all day with heaviest impact 11:00–14:00",
            "impact_direction": "negative",
            "impact_magnitude": 0.6,
            "impact_conf": 0.85,
            "reasoning": "Mostly overcast with morning showers clearing by early afternoon. Net negative effect on foot traffic, particularly lunch period.",
        }
    })

    # 2. Road closure signal
    # impact_direction: negative, uplift: -5%, conf: 0.95, description: 'Partial road closure 0.2km away, reduces pedestrian approach from the north', active hours 14:00–22:00
    signals.append({
        "location_id": location_id,
        "signal_type": "live_traffic",
        "forecast_date": "2026-03-23",
        "uplift_pct": -0.05,
        "signal_conf": 0.95,
        "label": "Road Closure - George Street Northbound (Hazard)",
        "distance_km": 0.2,
        "source_url": "synthetic",
        "description": "Partial road closure 0.2km away, LIVE Traffic NSW confirmed. Reduces pedestrian approach from the north.",
        "extra": {
            "start_hour": 14,
            "end_hour": 22,
        }
    })

    # 3. Competitor closure signal
    # impact_direction: positive, uplift: +7%, conf: 0.88, description: 'Nearby competitor detected as permanently closed 4 days ago, 0.4km away. Demand redistribution ongoing', active all day
    signals.append({
        "location_id": location_id,
        "signal_type": "google_places",
        "forecast_date": "2026-03-23",
        "uplift_pct": 0.07,
        "signal_conf": 0.88,
        "label": "Bob's Burgers George Street - Permanently Closed",
        "distance_km": 0.4,
        "source_url": "synthetic",
        "description": "Nearby competitor detected as permanently closed 4 days ago, 0.4km away. Demand redistribution ongoing",
        "extra": {
            "start_hour": 6,
            "end_hour": 23,
        }
    })

    # 4. Major event — April 21 May 2026
    # George Street Night Market running along the pedestrianised strip.
    # High foot traffic directly past the location from 17:00–23:00.
    # uplift: +18%, conf: 0.92, active hours: 17:00–23:00
    signals.append({
        "location_id": location_id,
        "signal_type": "eventbrite",
        "forecast_date": "2026-05-21",
        "uplift_pct": 0.18,
        "signal_conf": 0.92,
        "label": "George Street Night Market — Friday Autumn Edition",
        "distance_km": 0.1,
        "source_url": "synthetic",
        "description": "Street food and night market running along George Street from Town Hall to Circular Quay. High foot traffic directly past the location expected 17:00–23:00. Strong uplift likely across dinner and late evening.",
        "extra": {
            "start_hour": 17,
            "end_hour": 23,
            "crowd_type": "transit",
            "relevance_score": 0.92,
            "venue": "George Street, Sydney CBD",
            "capacity": 500,
            "impact_direction": "positive",
            "impact_magnitude": 0.18,
            "reasoning": "Outdoor night market on the pedestrianised George Street strip. Estimated 500 attendees walking past over the evening. Crowds actively looking for food and drinks — strong direct uplift to nearby fast food.",
        }
    })

    # 5. Major event — Friday 21 April 2026
    # NRL match: NSW Waratahs vs Brumbies at Allianz Stadium, Sydney.
    # Kick-off 19:35, match end ~21:35. Pre/post-game foot traffic uplift.
    # uplift: +22%, conf: 0.88, active hours: 17:00–23:00
    signals.append({
        "location_id": location_id,
        "signal_type": "sporting_event",
        "forecast_date": "2026-04-21",
        "uplift_pct": 0.22,
        "signal_conf": 0.88,
        "label": "NRL — NSW Waratahs vs Brumbies @ Allianz Stadium",
        "distance_km": 1.2,
        "source_url": "synthetic",
        "description": "NRL fixture between NSW Waratahs and Brumbies at Allianz Stadium, Sydney. Kick-off 19:35, estimated end 21:35. Pre-game crowds expected from ~17:00 as fans travel through the surrounding precinct. Post-game dispersal spike anticipated 21:30–23:00. Strong uplift likely across early dinner and late-night windows.",
        "extra": {
            "start_hour": 17,
            "end_hour": 23,
            "crowd_type": "sports_fan",
            "relevance_score": 0.88,
            "venue": "Allianz Stadium, Sydney",
            "capacity": 20000,
            "impact_direction": "positive",
            "impact_magnitude": 0.22,
            "reasoning": "Large-capacity NRL venue drawing ~20,000 attendees. Pre-game ingress from ~17:00 and post-game egress spike at ~21:35 drives strong foot traffic through nearby food and beverage outlets. Sports crowds are high-intent QSR consumers — elevated uplift expected across the full evening window.",
            "match": {
                "competition": "NRL",
                "home_team": "NSW Waratahs",
                "away_team": "Brumbies",
                "kickoff": "19:35",
                "estimated_end": "21:35",
                "match_date": "2026-05-22",
            }
        }
    })

    # Expand every signal into per-hour rows with proper UTC forecast_dt keys.
    # This replaces bare date strings like "2026-03-23" with UTC hour buckets
    # so they match the key format used by predictions and lookups.
    hourly_rows = []

    for s in signals:
        date_str = s["forecast_date"]
        extra = s.get("extra") or {}
        start_hour = extra.get("start_hour", 0)
        end_hour = extra.get("end_hour", 23)

        for h in range(start_hour, end_hour + 1):
            hourly_rows.append({
                "location_id": s["location_id"],
                "signal_type": s["signal_type"],
                "forecast_dt": _sydney_to_utc(date_str, h),
                "uplift_pct": s["uplift_pct"],
                "signal_conf": s["signal_conf"],
                "label": s["label"],
                "description": s.get("description"),
                "distance_km": s["distance_km"],
                "source_url": s["source_url"],
                "extra": s.get("extra"),
            })

    # Write synthetic signals to DB
    with db.db_session() as conn:
        conn.execute("DELETE FROM processed_signals WHERE source_url = 'synthetic' AND location_id = ?", (location_id,))
        for r in hourly_rows:
            conn.execute(
                """
                INSERT INTO processed_signals
                (location_id, signal_type, forecast_dt, uplift_pct, signal_conf, label, description, distance_km, source_url, extra_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    location_id,
                    r["signal_type"],
                    r["forecast_dt"],
                    r["uplift_pct"],
                    r["signal_conf"],
                    r["label"],
                    r.get("description"),
                    r["distance_km"],
                    r["source_url"],
                    json.dumps(r.get("extra")) if r.get("extra") is not None else None,
                ),
            )
