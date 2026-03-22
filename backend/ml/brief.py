from __future__ import annotations

import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import database as db
from config import settings

_SYDNEY_TZ = ZoneInfo("Australia/Sydney")


def _utc_to_sydney_label(utc_iso: str) -> str:
    """Convert a UTC ISO string to a human-readable Sydney local time label.

    Example output: '7:00 PM, Monday 23 Mar'
    """
    raw = utc_iso.strip()
    has_zone = raw.endswith("Z") or raw[-6] in ("+", "-")
    iso = raw if has_zone else f"{raw[:19]}+00:00"
    iso = iso.replace("Z", "+00:00")
    dt = datetime.fromisoformat(iso).astimezone(_SYDNEY_TZ)
    return dt.strftime("%-I:%M %p, %A %-d %b")


def generate_brief(location_id: str, target_date: str) -> str:
    """Plain English brief via Gemini; falls back to template if no API key."""
    # Fix 4: clear stale cached brief so we always regenerate
    db.delete_daily_brief(location_id, target_date)

    hours = db.get_predictions_for_date(location_id, target_date)
    if not hours:
        return "No forecast yet for this date. Run signal refresh and prediction from settings."

    peak_hour = max(hours, key=lambda h: h["busyness_index"])
    signals = db.get_processed_signals_for_hour(location_id, peak_hour["forecast_dt"])

    # Fix 3: convert UTC forecast_dt to human-readable Sydney time for the LLM
    peak_label = _utc_to_sydney_label(peak_hour["forecast_dt"])

    loc = db.get_location(location_id) or {}
    profile = {
        "business_type": loc.get("business_type", "restaurant"),
        "max_staff": loc.get("max_staff", 5),
    }

    payload = {
        "peak_hour": peak_label,
        "busyness_index": peak_hour["busyness_index"],
        "deviation_pct": peak_hour["deviation_pct"],
        "forecast_confidence": peak_hour["forecast_confidence"],
        "signals": [
            {
                "label": s["label"],
                "uplift_pct": s["uplift_pct"],
                "signal_conf": s["signal_conf"],
                "distance_km": s.get("distance_km"),
            }
            for s in signals
        ],
        "business_type": profile["business_type"],
        "max_staff": profile["max_staff"],
    }

    prompt = f"""
You are writing a demand forecast brief for a {payload['business_type']} manager.
Use only the data provided. Do not invent numbers.
Write exactly 3 sentences in plain English.
Do not mention AI, models, or algorithms.

Data:
{json.dumps(payload, indent=2)}

Output format:
Sentence 1: What is coming and when (busyness index and deviation from normal).
Sentence 2: The main signal driving this and why.
Sentence 3: The staffing recommendation using max_staff as the ceiling.
"""

    key = settings.openrouter_api_key
    if not key:
        return _template_brief(payload)

    try:
        import requests

        resp = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "google/gemini-3.1-flash-lite-preview",
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"].get("content", "").strip()
        if text:
            db.save_daily_brief(location_id, target_date, text)
            return text
    except Exception:
        pass

    text = _template_brief(payload)
    db.save_daily_brief(location_id, target_date, text)
    return text


def _template_brief(payload: dict) -> str:
    peak = payload["peak_hour"]
    bi = payload["busyness_index"]
    dev = payload["deviation_pct"]
    ms = payload["max_staff"]
    drivers = payload["signals"][:3]
    driver_txt = (
        ", ".join(f"{d['label']} ({d['uplift_pct']*100:.1f}% uplift)" for d in drivers)
        if drivers
        else "seasonal trading patterns"
    )
    rec = max(1, min(ms, int(round(ms * (1 + max(dev, 0) / 100.0)))))
    return (
        f"Peak demand is expected around {peak} with a busyness index of {bi}, "
        f"about {dev}% versus your usual level for that hour. "
        f"The main drivers look like: {driver_txt}. "
        f"Plan for up to {rec} staff on the floor (ceiling {ms})."
    )
