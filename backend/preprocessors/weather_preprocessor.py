from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo
import hashlib
import json

from config import FORECAST_HORIZON_DAYS

_SYDNEY_TZ = ZoneInfo("Australia/Sydney")
from preprocessors.common import parse_dt
import database as db
from llm.relevance_filter import llm_weather_relevance


def determine_outlier_label(outlier_hours: list[str], hourly: dict[str, Any]) -> str:
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

    if "Storm" in labels: return "Storm"
    if "Heatwave" in labels: return "Heatwave"
    if "Heavy rain" in labels: return "Heavy rain"
    if "Cold snap" in labels: return "Cold snap"
    return "Weather outlier"


def get_conditions(codes: list[int]) -> str:
    if not codes:
        return "Unknown"
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
    # 1. Fetch Location profile
    loc = db.get_location(location_id)
    business_profile = {
        "business_type": loc.get("business_type", "business") if loc else "business",
        "business_name": "the location",
        "address": loc.get("address", "Sydney") if loc else "Sydney",
    }
    
    hourly = raw_json.get("hourly") or {}
    times = hourly.get("time") or []
    temps = hourly.get("temperature_2m") or []
    precips = hourly.get("precipitation") or []
    codes = hourly.get("weathercode") or [0] * len(times)
    winds = hourly.get("wind_speed_10m") or [0] * len(times)

    if not times:
        return []

    # Map by day (YYYY-MM-DD)
    days_map = {}
    for i, t in enumerate(times):
        dt = parse_dt(t)
        if dt:
            day_str = dt.strftime("%Y-%m-%d")
            if day_str not in days_map:
                days_map[day_str] = {"times": [], "temps": [], "precips": [], "codes": [], "winds": []}
            days_map[day_str]["times"].append(t)
            days_map[day_str]["temps"].append(float(temps[i]) if (i < len(temps) and temps[i] is not None) else 20.0)
            days_map[day_str]["precips"].append(float(precips[i]) if (i < len(precips) and precips[i] is not None) else 0.0)
            days_map[day_str]["codes"].append(int(codes[i]) if (i < len(codes) and codes[i] is not None) else 0)
            days_map[day_str]["winds"].append(float(winds[i]) if (i < len(winds) and winds[i] is not None) else 0.0)

    now = datetime.now(timezone.utc)
    
    # 2. Compute basic stats and check cache / heuristics per day
    days_to_eval = []
    cached_or_default_results = {}
    
    for day_str, data in days_map.items():
        dt = parse_dt(data["times"][0])
        if dt is None:
            continue
            
        temp_high = max(data["temps"])
        temp_low = min(data["temps"])
        total_rain = sum(data["precips"])
        max_wind = max(data["winds"])
        conditions = get_conditions(data["codes"])
        
        outlier_hours = []
        for i, hour_t in enumerate(data["times"]):
            t_val = data["temps"][i]
            r_val = data["precips"][i]
            if r_val >= 5 or t_val >= 38 or t_val <= 10:
                outlier_hours.append(hour_t)

        is_outlier = len(outlier_hours) > 0
        outlier_label = determine_outlier_label(outlier_hours, hourly) if is_outlier else None
        
        # Format hash string strictly on weather factors
        hash_str = f"{temp_high:.1f}_{temp_low:.1f}_{total_rain:.1f}_{max_wind:.1f}_{conditions}_{is_outlier}_{outlier_label}"
        weather_hash = hashlib.md5(hash_str.encode()).hexdigest()
        
        days_map[day_str]["temp_high"] = temp_high
        days_map[day_str]["temp_low"] = temp_low
        days_map[day_str]["total_rain"] = total_rain
        days_map[day_str]["max_wind"] = max_wind
        days_map[day_str]["conditions"] = conditions
        days_map[day_str]["is_outlier"] = is_outlier
        days_map[day_str]["outlier_label"] = outlier_label
        days_map[day_str]["outlier_hours_str"] = f"{outlier_hours[0][11:16]}–{outlier_hours[-1][11:16]}" if is_outlier else None
        
        # Pre-filter unremarkable days
        unremarkable = (
            18 <= temp_high <= 28 and 
            total_rain < 2.0 and 
            max_wind < 20.0 and 
            not is_outlier
        )
        
        if unremarkable:
            cached_or_default_results[day_str] = {
                "impact_direction": "neutral",
                "impact_magnitude": 0.0,
                "impact_conf": 1.0,
                "reasoning": "Unremarkable weather day (mild temp, no rain, low wind).",
            }
            continue
            
        # Check DB Cache
        cache_row = db.get_weather_llm_cache(location_id, day_str)
        if cache_row and cache_row["weather_hash"] == weather_hash:
            cached_or_default_results[day_str] = cache_row
            continue
            
        # Needs LLM Evaluation
        days_to_eval.append({
            "forecast_date": day_str,
            "weather_hash": weather_hash,
            "temp_high": round(temp_high, 1),
            "temp_low": round(temp_low, 1),
            "total_rain_mm": round(total_rain, 1),
            "max_wind_kmh": round(max_wind, 1),
            "conditions": conditions,
            "severe_weather_flag": outlier_label if is_outlier else False
        })
        
    # 3. Batch LLM call and save to cache
    if days_to_eval:
        llm_results = llm_weather_relevance(days_to_eval, business_profile, location_id)
        rows_to_save = []
        for res in llm_results:
            d = res.get("forecast_date")
            if not d: continue
            
            whash = next((x["weather_hash"] for x in days_to_eval if x["forecast_date"] == d), "fallback")
            cached_or_default_results[d] = res
            
            rows_to_save.append({
                "location_id": location_id,
                "forecast_date": d,
                "weather_hash": whash,
                "impact_direction": res.get("impact_direction", "neutral"),
                "impact_magnitude": res.get("impact_magnitude", 0.0),
                "impact_conf": res.get("impact_conf", 0.70),
                "reasoning": res.get("reasoning", "No reasoning provided."),
            })
            
        db.save_weather_llm_cache(rows_to_save)

    # 4. Compile Final processed signals
    out: list[dict[str, Any]] = []
    
    for day_str, data in days_map.items():
        dt = parse_dt(data["times"][0])
        if dt is None: continue
            
        # Horizon decay base
        hours_until = (dt - now).total_seconds() / 3600.0
        if hours_until <= 48:
            horizon_conf = 0.99
        elif hours_until <= 72:
            horizon_conf = 0.96
        elif hours_until <= 120:
            horizon_conf = 0.95
        else:
            horizon_conf = 0.91
            
        # Blend confidences
        res = cached_or_default_results.get(day_str, {})
        impact_conf = float(res.get("impact_conf", 0.70))
        final_conf = min(0.99, horizon_conf * impact_conf)
        
        impact_direction = str(res.get("impact_direction", "neutral")).lower()
        impact_magnitude = float(res.get("impact_magnitude", 0.0))
        reasoning = str(res.get("reasoning", ""))
        
        # Map magnitude to uplift pct (-50% to +20%)
        uplift = 0.0
        if impact_direction == "negative":
            uplift = -0.5 * impact_magnitude
        elif impact_direction == "positive":
            uplift = 0.2 * impact_magnitude
            
        extra = {
            "temp_low": round(data["temp_low"], 1),
            "temp_high": round(data["temp_high"], 1),
            "total_rain_mm": round(data["total_rain"], 1),
            "conditions": data["conditions"],
            "start_hour": 6,
            "end_hour": 23,
            "outlier": data["is_outlier"],
            "outlier_hours": data["outlier_hours_str"],
            "outlier_label": data["outlier_label"],
            "impact_direction": impact_direction,
            "impact_magnitude": impact_magnitude,
            "description": reasoning,
            "horizon_conf": horizon_conf,
            "impact_conf": impact_conf
        }
            
        out.append({
            "location_id": location_id,
            "signal_type": "open_meteo",
            "forecast_dt": day_str,
            "uplift_pct": round(uplift, 4),
            "signal_conf": round(final_conf, 4),
            "label": f"Weather summary — {dt.strftime('%A %-d %b')}",
            "distance_km": None,
            "source_url": "https://open-meteo.com/",
            "extra": extra,
            "description": reasoning, # Added description field here
        })

    # Open-Meteo hourly forecast is ~16 days; pad remaining horizon with neutral placeholders (no extra fetch).
    horizon_days = int(raw_json.get("forecast_horizon_days") or FORECAST_HORIZON_DAYS)
    now_syd = datetime.now(_SYDNEY_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    emitted_days = {r["forecast_dt"] for r in out}
    neutral_reasoning = (
        "No hourly weather forecast from Open-Meteo for this date; "
        "impact treated as neutral (beyond API hourly horizon)."
    )
    for offset in range(horizon_days):
        day_syd = now_syd + timedelta(days=offset)
        ds = day_syd.strftime("%Y-%m-%d")
        if ds in emitted_days:
            continue
        try:
            day_label = day_syd.strftime("%A %d %b")
        except ValueError:
            day_label = ds
        neutral_extra = {
            "temp_low": None,
            "temp_high": None,
            "total_rain_mm": 0.0,
            "conditions": "Not available",
            "start_hour": 6,
            "end_hour": 23,
            "outlier": False,
            "outlier_hours": None,
            "outlier_label": None,
            "impact_direction": "neutral",
            "impact_magnitude": 0.0,
            "description": neutral_reasoning,
            "horizon_conf": 0.5,
            "impact_conf": 1.0,
            "beyond_api_horizon": True,
        }
        out.append(
            {
                "location_id": location_id,
                "signal_type": "open_meteo",
                "forecast_dt": ds,
                "uplift_pct": 0.0,
                "signal_conf": 0.5,
                "label": f"Weather — {day_label} (neutral, beyond hourly API)",
                "distance_km": None,
                "source_url": "https://open-meteo.com/",
                "extra": neutral_extra,
                "description": neutral_reasoning,
            }
        )
        emitted_days.add(ds)
        
    if out:
        print(f"[WEATHER] Processed {len(out)} days. Example: {out[0]['forecast_dt']} -> {out[0]['label']}")

    return out
