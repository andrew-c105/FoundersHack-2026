from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from preprocessors.common import format_forecast_dt, parse_dt

import json

def determine_outlier_label(outlier_hours: list[str], hourly: dict[str, Any]) -> str:
    """Determine the most severe outlier label present."""
    labels = set()
    for t in outlier_hours:
        try:
            idx = hourly["time"].index(t)
            temp = float(hourly["temperature_2m"][idx])
            rain = float(hourly["precipitation"][idx])
            if rain >= 10:
                labels.add("Storm")
            elif rain >= 5:
                labels.add("Heavy rain")
            if temp >= 38:
                labels.add("Heatwave")
            if temp <= 10:
                labels.add("Cold snap")
        except (ValueError, IndexError):
            pass

    # Severity ranking
    if "Storm" in labels: return "Storm"
    if "Heatwave" in labels: return "Heatwave"
    if "Heavy rain" in labels: return "Heavy rain"
    if "Cold snap" in labels: return "Cold snap"
    return "Weather outlier"

def get_conditions(codes: list[int]) -> str:
    # simple mapping for dominant code
    if not codes:
        return "Unknown"
    # standard WMO codes
    c = max(set(codes), key=codes.count)
    if c == 0: return "Clear sky"
    if c in (1, 2, 3): return "Partly cloudy"
    if c in (45, 48): return "Fog"
    if c in (51, 53, 55, 56, 57): return "Drizzle"
    if c in (61, 63, 65, 66, 67): return "Rain"
    if c in (71, 73, 75, 77): return "Snow"
    if c in (80, 81, 82): return "Showers"
    if c >= 95: return "Thunderstorm"
    return "Cloudy"

def process_weather_signal(raw_json: dict[str, Any], location_id: str) -> list[dict[str, Any]]:
    """
    Open-Meteo hourly: temperature_2m, precipitation, weathercode (optional), time[]
    Aggregates full day's forecast into a single dict.
    """
    hourly = raw_json.get("hourly") or {}
    times = hourly.get("time") or []
    temps = hourly.get("temperature_2m") or []
    precips = hourly.get("precipitation") or []
    codes = hourly.get("weathercode") or [0] * len(times)

    if not times:
        return []

    # Map by day (YYYY-MM-DD)
    days_map = {}
    for i, t in enumerate(times):
        dt = parse_dt(t)
        if dt:
            day_str = dt.strftime("%Y-%m-%d")
            if day_str not in days_map:
                days_map[day_str] = {"times": [], "temps": [], "precips": [], "codes": []}
            days_map[day_str]["times"].append(t)
            days_map[day_str]["temps"].append(float(temps[i]) if (i < len(temps) and temps[i] is not None) else 20.0)
            days_map[day_str]["precips"].append(float(precips[i]) if (i < len(precips) and precips[i] is not None) else 0.0)
            days_map[day_str]["codes"].append(int(codes[i]) if (i < len(codes) and codes[i] is not None) else 0)

    now = datetime.now(timezone.utc)
    out: list[dict[str, Any]] = []

    for day_str, data in days_map.items():
        dt = parse_dt(data["times"][0])
        if dt is None:
            continue
            
        temp_high = max(data["temps"])
        temp_low = min(data["temps"])
        total_rain = sum(data["precips"])
        conditions = get_conditions(data["codes"])
        
        # Base uplift
        uplift = 0.0
        if temp_high > 24 and total_rain == 0:
            uplift += 0.12
        if temp_high > 28:
            uplift += 0.05
        if total_rain > 2:
            uplift -= 0.15
        if total_rain > 10:
            uplift -= 0.10
        if temp_low < 10:
            uplift -= 0.08

        # Outlier Detection
        outlier_hours = []
        for i, hour_t in enumerate(data["times"]):
            t_val = data["temps"][i]
            r_val = data["precips"][i]
            if r_val >= 5 or t_val >= 38 or t_val <= 10:
                outlier_hours.append(hour_t)

        extra = {
            "temp_low": round(temp_low, 1),
            "temp_high": round(temp_high, 1),
            "total_rain_mm": round(total_rain, 1),
            "conditions": conditions,
            "start_hour": 6,
            "end_hour": 23,
        }

        if outlier_hours:
            extra["outlier"] = True
            extra["outlier_hours"] = f"{outlier_hours[0][11:16]}–{outlier_hours[-1][11:16]}"
            extra["outlier_label"] = determine_outlier_label(outlier_hours, hourly)
        else:
            extra["outlier"] = False
            extra["outlier_hours"] = None
            extra["outlier_label"] = None

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

        # Description text based on weather 
        desc = f"{conditions} day."
        if extra["outlier"]:
            desc += f" {extra['outlier_label']} expected {extra['outlier_hours']}, reducing foot traffic significantly."
        elif uplift > 0:
            desc += f" Warm {conditions.lower()} day with negligible rainfall. Positive effect on foot traffic across trading hours."
        elif uplift < -0.1:
            desc += f" Wet weather likely to deter foot traffic. Consider lowering staffing levels."
            
        extra["description"] = desc

        # Hardcoded extreme event for user request: March 31st, 2026
        if day_str == "2026-03-31":
            extra["outlier"] = True
            extra["outlier_hours"] = "14:00–19:00"
            extra["outlier_label"] = "Thunderstorm"
            extra["description"] = "Severe thunderstorm expected 14:00–19:00, reducing foot traffic significantly. High flash flood risk."
            extra["total_rain_mm"] = 45.0
            uplift = -0.45

        out.append(
            {
                "location_id": location_id,
                "signal_type": "open_meteo",
                "forecast_dt": day_str,   # DATE ONLY, NOT PER-HOUR
                "uplift_pct": round(uplift, 4),
                "confidence": conf,
                "label": f"Weather summary — {dt.strftime('%A %-d %b')}",
                "distance_km": None,
                "source_url": "https://open-meteo.com/",
                "extra": extra,
            }
        )
    
    if out:
        print(f"[WEATHER] Processed {len(out)} days. Example: {out[0]['forecast_dt']} -> {out[0]['label']}")

    return out
