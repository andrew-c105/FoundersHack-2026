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
from ml.predict import get_alerts, predict_next_30_days
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
        preds = predict_next_30_days(location_id)
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="Train the model first") from None
    return {"count": len(preds)}


@router.post("/locations/{location_id}/bootstrap-model")
def bootstrap_model(location_id: str) -> dict:
    """Train XGBoost then run 30-day inference (typical post-onboarding flow)."""
    if not db.get_location(location_id):
        raise HTTPException(status_code=404, detail="Location not found")
    try:
        _, mae = train_model(location_id)
        preds = predict_next_30_days(location_id)
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
    peak = max(hours, key=lambda h: h["deviation_pct"]) if hours else None
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
