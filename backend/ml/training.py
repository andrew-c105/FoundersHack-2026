from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

import database as db
from config import settings
from preprocessors.common import format_forecast_dt


def _event_uplift(location_id: str, dt: datetime) -> float:
    key = format_forecast_dt(dt)
    return db.get_signal_uplift(location_id, ["ticketmaster", "eventbrite"], key)


def _event_conf(location_id: str, dt: datetime) -> float:
    key = format_forecast_dt(dt)
    return db.get_signal_confidence(location_id, ["ticketmaster", "eventbrite"], key, 0.1)


def _transport_total(location_id: str, dt: datetime) -> float:
    key = format_forecast_dt(dt)
    a = db.get_signal_uplift(location_id, ["transport_nsw"], key)
    b = db.get_signal_uplift(location_id, ["live_traffic"], key)
    return a + b


def build_training_table(location_id: str, history_days: int = 90) -> pd.DataFrame:
    """
    Builds rows for past `history_days`. Labels blend Popular Times baseline with
    synthetic signal-driven adjustment so XGBoost learns feature interactions (hackathon path).
    """
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    rows: list[dict[str, Any]] = []
    rng = np.random.default_rng(42)

    for h_back in range(history_days * 24, 0, -1):
        dt = now - timedelta(hours=h_back)
        dow = dt.weekday()
        hour = dt.hour
        key = format_forecast_dt(dt)

        event_uplift = _event_uplift(location_id, dt)
        event_conf = _event_conf(location_id, dt)
        day_key = dt.strftime("%Y-%m-%d")
        weather_uplift = db.get_signal_uplift(location_id, ["open_meteo"], day_key)
        weather_conf = db.get_signal_confidence(location_id, ["open_meteo"], day_key, 0.5)
        competitor_shift = db.get_signal_uplift(location_id, ["google_places"], key)
        transport_impact = _transport_total(location_id, dt)
        school_holiday = db.get_signal_uplift(location_id, ["static_school"], key)
        public_holiday = db.get_signal_uplift(location_id, ["static_holiday"], key)
        sporting_fixture = db.get_signal_uplift(location_id, ["static_sport"], key)
        uni_calendar = db.get_signal_uplift(location_id, ["static_uni"], key)

        baseline = db.get_popular_times_baseline(location_id, dow, hour)

        # Replay approximate feature evolution: dampen older random noise
        noise = rng.normal(0, 3.0)
        adjusted = baseline + 55.0 * (
            event_uplift * event_conf
            + 0.8 * weather_uplift * weather_conf
            + competitor_shift
            + transport_impact
            + school_holiday
            + public_holiday
            + sporting_fixture
            + uni_calendar
        )
        popular_times_score = float(np.clip(adjusted + noise, 0, 100))

        rows.append(
            {
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
                "popular_times_score": popular_times_score,
            }
        )

    return pd.DataFrame(rows)


def train_model(location_id: str) -> tuple[XGBRegressor, float]:
    df = build_training_table(location_id)
    feature_cols = [
        "day_of_week",
        "hour",
        "event_uplift",
        "event_conf",
        "weather_uplift",
        "weather_conf",
        "competitor_shift",
        "transport_impact",
        "school_holiday",
        "public_holiday",
        "sporting_fixture",
        "uni_calendar",
    ]
    X = df[feature_cols]
    y = df["popular_times_score"]

    if len(df) < 50:
        raise ValueError("Not enough training rows")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    model = XGBRegressor(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        random_state=42,
    )
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, preds))
    db.log_accuracy(location_id, mae, "mae")

    path = settings.models_dir / f"xgb_{location_id}.pkl"
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)
    return model, mae


def load_model(location_id: str) -> XGBRegressor:
    path = settings.models_dir / f"xgb_{location_id}.pkl"
    if not path.exists():
        raise FileNotFoundError(path)
    return joblib.load(path)
