import os
import json
import logging
from typing import Any

import database as db

logger = logging.getLogger(__name__)

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
        "forecast_dt": "2026-03-23",
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
        "forecast_dt": "2026-03-23",
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
        "forecast_dt": "2026-03-23",
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

    # Also map these into per-hour rows for the ML model predict pipeline if needed
    hourly_rows = []
    
    # Static daily representations without hour specificity
    hourly_rows.extend(signals)
    
    # Generate explicit hourly rows for traffic and places if the pipeline expects them
    for s in signals:
        if s["signal_type"] == "live_traffic":
            for h in range(14, 23):
                hourly_rows.append({
                    **s,
                    "forecast_dt": f"2026-03-23T{h:02d}:00:00"
                })
        elif s["signal_type"] == "google_places":
            for h in range(6, 24):
                hourly_rows.append({
                    **s,
                    "forecast_dt": f"2026-03-23T{h:02d}:00:00"
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
