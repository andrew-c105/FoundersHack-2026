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

    # 4. Major event — April 21 May 2026
    # George Street Night Market running along the pedestrianised strip.
    # High foot traffic directly past the location from 17:00–23:00.
    # uplift: +18%, conf: 0.92, active hours: 17:00–23:00
    signals.append({
        "location_id": location_id,
        "signal_type": "eventbrite",
        "forecast_dt": "2026-05-21",
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
        "forecast_dt": "2026-04-21",
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
        elif s["signal_type"] in ("eventbrite", "sporting_event") and s.get("forecast_dt") == "2026-05-22":
            for h in range(17, 24):
                hourly_rows.append({
                    **s,
                    "forecast_dt": f"2026-05-22T{h:02d}:00:00"
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
