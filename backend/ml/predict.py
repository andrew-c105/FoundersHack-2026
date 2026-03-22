from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import pandas as pd

import database as db
from ml.training import load_model
from preprocessors.common import format_forecast_dt


def next_30_days_hourly(start: Optional[datetime] = None):
    if start is None:
        start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    for i in range(30 * 24):
        yield start + timedelta(hours=i)


def predict_next_30_days(location_id: str) -> list[dict[str, Any]]:
    model = load_model(location_id)
    predictions: list[dict[str, Any]] = []

    for dt in next_30_days_hourly():
        dow = dt.weekday()
        hour = dt.hour
        key = format_forecast_dt(dt)

        event_uplift = db.get_signal_uplift(location_id, ["ticketmaster", "eventbrite"], key)
        event_conf = db.get_signal_confidence(location_id, ["ticketmaster", "eventbrite", "static_sport"], key, 0.99)
        day_key = dt.strftime("%Y-%m-%d")
        weather_uplift = db.get_signal_uplift(location_id, ["open_meteo"], day_key)
        weather_conf = db.get_signal_confidence(location_id, ["open_meteo"], day_key, 0.5)
        competitor_shift = db.get_signal_uplift(location_id, ["google_places"], key)
        transport_impact = db.get_signal_uplift(location_id, ["transport_nsw"], key) + db.get_signal_uplift(
            location_id, ["live_traffic"], key
        )
        school_holiday = db.get_signal_uplift(location_id, ["static_school"], key)
        public_holiday = db.get_signal_uplift(location_id, ["static_holiday"], key)
        sporting_fixture = db.get_signal_uplift(location_id, ["static_sport"], key)
        uni_calendar = db.get_signal_uplift(location_id, ["static_uni"], key)

        features = {
            "day_of_week": dow,
            "hour": hour,
            "event_uplift": event_uplift,
            "event_conf": event_conf,
            "weather_uplift": weather_uplift,
            "weather_conf": weather_conf,
            "competitor_shift": competitor_shift,
            "transport_impact": transport_impact,
            "school_holiday": school_holiday,
            "public_holiday": public_holiday,
            "sporting_fixture": sporting_fixture,
            "uni_calendar": uni_calendar,
        }

        # The model predicts a baseline-level score from (dow, hour) features.
        # We then apply real-time signal uplifts explicitly on top so the
        # predicted score actually diverges from baseline when signals are present.
        model_score = float(model.predict(pd.DataFrame([features]))[0])

        total_signal_uplift = (
            event_uplift * event_conf
            + 0.8 * weather_uplift * weather_conf
            + competitor_shift
            + transport_impact
            + school_holiday
            + public_holiday
            + sporting_fixture
            + uni_calendar
        )
        # Scale uplift_pct (fractional, e.g. 0.12) into busyness-index units
        signal_delta = total_signal_uplift * 55.0

        predicted_score = round(max(0, min(100, model_score + signal_delta)))

        baseline_score = db.get_popular_times_baseline(location_id, dow, hour)
        if baseline_score and baseline_score > 0:
            deviation_pct = round((predicted_score - baseline_score) / baseline_score * 100)
        else:
            deviation_pct = 0

        forecast_confidence = round(
            (features["event_conf"] + features["weather_conf"] + 0.99 + 0.99) / 4,
            2,
        )

        print(
            f"[PREDICT] {key} dow={dow} h={hour:02d} "
            f"model={model_score:.1f} signal_delta={signal_delta:+.1f} "
            f"predicted={predicted_score} baseline={baseline_score:.1f} dev={deviation_pct:+d}%"
        )

        predictions.append(
            {
                "location_id": location_id,
                "forecast_dt": key,
                "busyness_index": predicted_score,
                "baseline_score": baseline_score,
                "deviation_pct": deviation_pct,
                "forecast_confidence": forecast_confidence,
            }
        )

    db.write_predictions(predictions)
    return predictions


def get_alerts(location_id: str, threshold_pct: int = 30) -> list[dict[str, Any]]:
    preds = db.get_predictions_for_location(location_id)
    return [p for p in preds if p["deviation_pct"] >= threshold_pct]
