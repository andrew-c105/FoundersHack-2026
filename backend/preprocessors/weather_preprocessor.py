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

    now = datetime.now(timezone.utc)
    out: list[dict[str, Any]] = []

    for i, t in enumerate(times):
        temp = float(temps[i]) if i < len(temps) else 20.0
        precip = float(precips[i]) if i < len(precips) else 0.0
        _wc = int(codes[i]) if i < len(codes) else 0

        dt = parse_dt(t)
        if dt is None:
            continue
        dt = dt.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)

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
                "forecast_dt": format_forecast_dt(dt),
                "uplift_pct": uplift,
                "confidence": conf,
                "label": f"Weather {temp:.0f}°C, rain {precip:.1f}mm",
                "distance_km": None,
                "source_url": "https://open-meteo.com/",
            }
        )

    return out
