from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException

import database as db
from api.schemas import LocationUpdate, OnboardingRequest
from ml.brief import generate_brief
from ml.predict import get_alerts, predict_forecast_horizon
from ml.training import train_model
from services.pipeline import create_location_from_onboarding, refresh_signals_for_location

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/locations/onboarding")
def onboarding(body: OnboardingRequest) -> dict:
    loc_id = create_location_from_onboarding(
        business_type=body.business_type,
        address=body.address,
        max_staff=body.max_staff,
        trading_hours=body.trading_hours,
        signal_toggles=body.signal_toggles,
    )
    return {"location_id": loc_id}


@router.get("/locations")
def list_locations() -> list[dict]:
    return db.list_locations()


@router.get("/locations/{location_id}")
def get_location(location_id: str) -> dict:
    loc = db.get_location(location_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    return loc


@router.patch("/locations/{location_id}")
def patch_location(location_id: str, body: LocationUpdate) -> dict:
    loc = db.get_location(location_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    fields: dict = {}
    if body.business_type is not None:
        fields["business_type"] = body.business_type
    if body.address is not None:
        fields["address"] = body.address
    if body.max_staff is not None:
        fields["max_staff"] = body.max_staff
    if body.trading_hours is not None:
        fields["trading_hours_json"] = json.dumps(body.trading_hours)
    if body.signal_toggles is not None:
        fields["signal_toggles_json"] = json.dumps(body.signal_toggles)
    db.update_location(location_id, fields)
    return db.get_location(location_id)  # type: ignore


@router.post("/locations/{location_id}/refresh")
def refresh(location_id: str) -> dict:
    if not db.get_location(location_id):
        raise HTTPException(status_code=404, detail="Location not found")
    refresh_signals_for_location(location_id)
    return {"status": "refreshed"}


@router.post("/locations/{location_id}/train")
def train(location_id: str) -> dict:
    if not db.get_location(location_id):
        raise HTTPException(status_code=404, detail="Location not found")
    try:
        _, mae = train_model(location_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"status": "trained", "mae": mae}


@router.post("/locations/{location_id}/predict")
def predict(location_id: str) -> dict:
    if not db.get_location(location_id):
        raise HTTPException(status_code=404, detail="Location not found")
    try:
        preds = predict_forecast_horizon(location_id)
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="Train the model first") from None
    return {"count": len(preds)}


@router.post("/locations/{location_id}/bootstrap-model")
def bootstrap_model(location_id: str) -> dict:
    """Train XGBoost then run full-horizon inference (typical post-onboarding flow)."""
    if not db.get_location(location_id):
        raise HTTPException(status_code=404, detail="Location not found")
    try:
        _, mae = train_model(location_id)
        preds = predict_forecast_horizon(location_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"mae": mae, "predictions": len(preds)}


@router.get("/locations/{location_id}/predictions")
def predictions(location_id: str, start: Optional[str] = None, end: Optional[str] = None) -> List[dict]:
    if not db.get_location(location_id):
        raise HTTPException(status_code=404, detail="Location not found")
    return db.get_predictions_for_location(location_id, start, end)


@router.get("/locations/{location_id}/brief")
def brief(location_id: str, date: Optional[str] = None) -> dict:
    if not db.get_location(location_id):
        raise HTTPException(status_code=404, detail="Location not found")
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    text = db.get_daily_brief(location_id, date)
    if not text:
        text = generate_brief(location_id, date)
    hours = db.get_predictions_for_date(location_id, date)
    peak = max(hours, key=lambda h: h["busyness_index"]) if hours else None
    return {"date": date, "brief": text, "peak_hour": peak, "hours": hours}


@router.get("/locations/{location_id}/alerts")
def alerts(location_id: str, threshold: int = 30) -> list[dict]:
    if not db.get_location(location_id):
        raise HTTPException(status_code=404, detail="Location not found")
    return get_alerts(location_id, threshold)


@router.get("/locations/{location_id}/map-signals")
def map_signals(location_id: str) -> dict:
    loc = db.get_location(location_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    rows = db.get_map_signals(location_id)
    clat, clng = float(loc["lat"]), float(loc["lng"])
    markers = []
    for i, s in enumerate(rows):
        h = int(hashlib.md5(f"{s.get('label')}{i}".encode()).hexdigest()[:8], 16)
        ang = (h % 360) * math.pi / 180.0
        r = 0.002 + (h % 80) / 40000.0
        markers.append(
            {
                **dict(s),
                "lat": clat + r * math.cos(ang),
                "lng": clng + r * math.sin(ang),
                "positive": float(s.get("uplift_pct") or 0) >= 0,
            }
        )
    return {
        "center": {"lat": clat, "lng": clng},
        "signals": rows,
        "markers": markers,
    }


@router.get("/locations/{location_id}/accuracy")
def accuracy(location_id: str) -> dict:
    if not db.get_location(location_id):
        raise HTTPException(status_code=404, detail="Location not found")
    hist = db.get_accuracy_history(location_id)
    return {"history": hist}


@router.get("/locations/{location_id}/signals/hour")
def signals_hour(location_id: str, forecast_dt: str) -> list[dict]:
    if not db.get_location(location_id):
        raise HTTPException(status_code=404, detail="Location not found")
    return db.get_processed_signals_for_hour(location_id, forecast_dt)


@router.get("/locations/{location_id}/event-reasoning")
def event_reasoning(location_id: str, date: Optional[str] = None) -> dict:
    if not db.get_location(location_id):
        raise HTTPException(status_code=404, detail="Location not found")
    rows = db.get_event_reasoning(location_id, date)
    included = [r for r in rows if r["include"]]
    excluded = [r for r in rows if not r["include"]]
    return {
        "included": included,
        "excluded": excluded,
        "total_evaluated": len(rows),
        "included_count": len(included),
        "excluded_count": len(excluded),
    }


@router.get("/locations/{location_id}/event-reasoning/debug")
def event_reasoning_debug(location_id: str, event_name: str) -> dict:
    if not db.get_location(location_id):
        raise HTTPException(status_code=404, detail="Location not found")
    row = db.get_event_reasoning_debug(location_id, event_name)
    if not row:
        return {"error": "No reasoning found for this event"}
    return {
        "event_name": row["event_name"],
        "relevance_score": row["relevance_score"],
        "crowd_type": row["crowd_type"],
        "reason": row["reason"],
        "include": bool(row["include"]),
        "scored_at": row["scored_at"],
        "prompt_used": row.get("prompt_used"),
        "raw_llm_response": row.get("raw_llm_response"),
    }


def _nonempty_str(val: object) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


@router.get("/locations/{location_id}/signals/day")
def signals_day(location_id: str, date: str) -> dict:
    """Return deduplicated signals active on a date with start/end hour ranges."""
    if not db.get_location(location_id):
        raise HTTPException(status_code=404, detail="Location not found")

    from collections import defaultdict

    all_signals = db.get_processed_signals_for_date(location_id, date)

    import json
    
    # Group by signal label → aggregate hours
    grouped: dict = defaultdict(lambda: {
        "signal_type": "",
        "label": "",
        "uplift_pct": 0.0,
        "signal_conf": 0.0,
        "distance_km": None,
        "source_url": "",
        "impact_direction": "neutral",
        "impact_magnitude": 0.0,
        "extra": {},
        "hours": [],
        "description_col": None,
    })

    for s in all_signals:
        key = s.get("label") or s.get("signal_type", "unknown")
        g = grouped[key]
        g["signal_type"] = s.get("signal_type", "")
        g["label"] = key
        g["uplift_pct"] = max(g["uplift_pct"], abs(float(s.get("uplift_pct", 0))))
        if float(s.get("uplift_pct", 0)) < 0:
            g["uplift_pct"] = -g["uplift_pct"]
        g["signal_conf"] = max(g["signal_conf"], float(s.get("signal_conf", 0)))
        g["distance_km"] = s.get("distance_km") or g["distance_km"]
        g["source_url"] = s.get("source_url") or g["source_url"]
        dbt = _nonempty_str(s.get("description"))
        if dbt:
            prev = _nonempty_str(g.get("description_col"))
            if not prev or len(dbt) > len(prev):
                g["description_col"] = dbt

        # Unpack extra_json
        ej = s.get("extra_json")
        if ej:
            try:
                ex = json.loads(ej)
                g["extra"].update(ex)
                if "impact_direction" in ex: g["impact_direction"] = ex["impact_direction"]
                if "impact_magnitude" in ex: g["impact_magnitude"] = ex["impact_magnitude"]
            except json.JSONDecodeError:
                pass

        fdt = s.get("forecast_dt", "")
        if len(fdt) >= 13:
            h = int(fdt[11:13])
            g["hours"].append(h)

    signals_out = []
    for key, g in grouped.items():
        if g["signal_type"] == "open_meteo":
            impact_dir = g["extra"].get("impact_direction")
            impact_mag = float(g["extra"].get("impact_magnitude", 0))
            if impact_dir != "negative" or impact_mag <= 0.3:
                continue

        hours = sorted(set(g["hours"]))
        # For signals that provided explicit bounds in extra_json (like weather or daily signals)
        start_hour = g["extra"].get("start_hour", hours[0] if hours else 0)
        end_hour = g["extra"].get("end_hour", hours[-1] if hours else 23)
        
        desc_col = _nonempty_str(g.get("description_col"))
        desc_extra = _nonempty_str(g["extra"].get("description"))
        desc_reason = _nonempty_str(g["extra"].get("reasoning"))
        final_description = desc_col or desc_extra or desc_reason

        sig_data = {
            "label": g["label"],
            "signal_type": g["signal_type"],
            "uplift_pct": round(g["uplift_pct"], 4),
            "signal_conf": round(g["signal_conf"], 2),
            "distance_km": g["distance_km"],
            "source_url": g["source_url"],
            "start_hour": start_hour,
            "end_hour": end_hour,
            "description": final_description,
            "impact_direction": g.get("impact_direction", "neutral"),
            "impact_magnitude": float(g.get("impact_magnitude", 0.0)),
        }
        
        # Inherit extra weather fields if present
        for f in [
            "temp_low",
            "temp_high",
            "total_rain_mm",
            "conditions",
            "outlier",
            "outlier_hours",
            "outlier_label",
            "outlier_alert",
        ]:
            if f in g["extra"]:
                sig_data[f] = g["extra"][f]
                
        signals_out.append(sig_data)

    # Get the brief for this date
    brief_text = ""
    try:
        brief_row = db.get_daily_brief(location_id, date)
        if brief_row:
            brief_text = brief_row.get("brief_text", "")
    except Exception:
        pass

    positive_count = sum(1 for s in signals_out if s["uplift_pct"] > 0)
    negative_count = sum(1 for s in signals_out if s["uplift_pct"] < 0)

    return {
        "date": date,
        "signals": signals_out,
        "brief": brief_text,
        "positive_count": positive_count,
        "negative_count": negative_count,
        "total_signals": len(signals_out),
    }


