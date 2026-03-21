from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from preprocessors.common import format_forecast_dt, parse_dt


def process_weather_signal(raw_json: dict[str, Any], location_id: str) -> list[dict[str, Any]]:
    """
    Open-Meteo hourly: temperature_2m, precipitation, weathercode (optional), time[]
    """
    hourly = raw_json.get("hourly") or {}
    times = hourly.get("time") or []
    temps = hourly.get("temperature_2m") or []
    precips = hourly.get("precipitation") or []
    codes = hourly.get("weathercode") or [0] * len(times)

    # Create a lookup map to ensure we match by time string, not just array position
    weather_map = {}
    for i, t in enumerate(times):
        dt = parse_dt(t)
        if dt:
            key = format_forecast_dt(dt)
            weather_map[key] = {
                "temp": float(temps[i]) if i < len(temps) else 20.0,
                "precip": float(precips[i]) if i < len(precips) else 0.0,
                "code": int(codes[i]) if i < len(codes) else 0,
                "original_time": t
            }

    now = datetime.now(timezone.utc)
    out: list[dict[str, Any]] = []

    for forecast_dt, data in weather_map.items():
        dt = parse_dt(forecast_dt)
        if dt is None:
            continue
            
        temp = data["temp"]
        precip = data["precip"]
        
        uplift = 0.0
        if temp > 24 and precip == 0:
            uplift += 0.12
        if temp > 28:
            uplift += 0.05
        if precip > 2:
            uplift -= 0.15
        if precip > 10:
            uplift -= 0.10
        if temp < 10:
            uplift -= 0.08

        hours_until = (dt - now).total_seconds() / 3600.0
        if hours_until <= 24:
            conf = 0.90
        elif hours_until <= 48:
            conf = 0.82
        elif hours_until <= 72:
            conf = 0.74
        elif hours_until <= 120:
            conf = 0.62
        else:
            conf = 0.50

        out.append(
            {
                "location_id": location_id,
                "signal_type": "open_meteo",
                "forecast_dt": forecast_dt,
                "uplift_pct": uplift,
                "confidence": conf,
                "label": f"Weather {temp:.0f}°C, rain {precip:.1f}mm",
                "distance_km": None,
                "source_url": "https://open-meteo.com/",
            }
        )
    
    if out:
        print(f"[WEATHER] Processed {len(out)} hours. Example mapping: {out[0]['forecast_dt']} -> {out[0]['label']}")

    return out
