from __future__ import annotations

import json
from datetime import datetime, timezone

import database as db
from config import settings


def generate_brief(location_id: str, target_date: str) -> str:
    """Plain English brief via Gemini; falls back to template if no API key."""
    hours = db.get_predictions_for_date(location_id, target_date)
    if not hours:
        return "No forecast yet for this date. Run signal refresh and prediction from settings."

    peak_hour = max(hours, key=lambda h: h["deviation_pct"])
    signals = db.get_processed_signals_for_hour(location_id, peak_hour["forecast_dt"])

    loc = db.get_location(location_id) or {}
    profile = {
        "business_type": loc.get("business_type", "restaurant"),
        "max_staff": loc.get("max_staff", 5),
    }

    payload = {
        "peak_hour": peak_hour["forecast_dt"],
        "busyness_index": peak_hour["busyness_index"],
        "deviation_pct": peak_hour["deviation_pct"],
        "confidence": peak_hour["confidence"],
        "signals": [
            {
                "label": s["label"],
                "uplift_pct": s["uplift_pct"],
                "confidence": s["confidence"],
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
                "model": "qwen/qwen3-235b-a22b",
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
