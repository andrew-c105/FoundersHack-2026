from __future__ import annotations

import json
import os
import uuid
from typing import Any

import database as db
from config import settings
from services.fetchers import (
    fetch_eventbrite_nearby,
    fetch_google_places_nearby,
    fetch_live_traffic_nsw,
    fetch_open_meteo,
    fetch_popular_times_raw,
    fetch_transport_nsw_sample,
    find_google_place_id,
    geocode_address,
)
from services.orchestrator import run_preprocessors


def _toggles(loc: dict[str, Any]) -> dict[str, bool]:
    raw = loc.get("signal_toggles_json")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _enabled(toggles: dict[str, bool], key: str, default: bool = True) -> bool:
    return bool(toggles.get(key, default))


def create_location_from_onboarding(
    business_type: str,
    address: str,
    max_staff: int,
    trading_hours: dict[str, Any],
    signal_toggles: dict[str, bool] | None = None,
) -> str:
    lat, lng, postcode, state = geocode_address(address)
    loc_id = f"loc_{uuid.uuid4().hex[:10]}"
    place_id = find_google_place_id(address, lat, lng)
    toggles = signal_toggles or {
        "open_meteo": True,
        "eventbrite": True,
        "google_places": True,
        "transport_nsw": True,
        "live_traffic": True,
        "static": True,
    }

    db.create_location(
        {
            "id": loc_id,
            "business_type": business_type,
            "address": address,
            "lat": lat,
            "lng": lng,
            "postcode": postcode,
            "state": state,
            "google_place_id": place_id,
            "max_staff": max_staff,
            "trading_hours_json": json.dumps(trading_hours),
            "signal_toggles_json": json.dumps(toggles),
        }
    )

    popular_raw = fetch_popular_times_raw(place_id or "", lat, lng)
    db.insert_raw_signal(loc_id, "popular_times", popular_raw)
    run_preprocessors(loc_id, "popular_times", popular_raw)

    refresh_signals_for_location(loc_id)
    return loc_id


def refresh_signals_for_location(location_id: str) -> None:
    loc = db.get_location(location_id)
    if not loc:
        return
    toggles = _toggles(loc)
    lat, lng = float(loc["lat"]), float(loc["lng"])
    state = loc.get("state") or "NSW"

    loc_ctx = {"lat": lat, "lng": lng}

    if _enabled(toggles, "open_meteo"):
        raw = fetch_open_meteo(lat, lng)
        db.insert_raw_signal(location_id, "open_meteo", raw)
        run_preprocessors(location_id, "open_meteo", raw)

    if _enabled(toggles, "eventbrite"):
        ev = fetch_eventbrite_nearby(lat, lng)
        db.insert_raw_signal(location_id, "eventbrite", ev)
        run_preprocessors(location_id, "eventbrite", ev)

    if _enabled(toggles, "google_places"):
        gp = fetch_google_places_nearby(lat, lng, loc.get("business_type", "restaurant"))
        gp["location"] = loc_ctx
        db.insert_raw_signal(location_id, "google_places", gp)
        run_preprocessors(location_id, "google_places", gp)

    if _enabled(toggles, "transport_nsw"):
        tr = fetch_transport_nsw_sample(lat, lng)
        tr["location"] = loc_ctx
        db.insert_raw_signal(location_id, "transport_nsw", tr)
        run_preprocessors(location_id, "transport_nsw", tr)

    if _enabled(toggles, "live_traffic"):
        lt = fetch_live_traffic_nsw(lat, lng)
        lt["location"] = loc_ctx
        db.insert_raw_signal(location_id, "live_traffic", lt)
        run_preprocessors(location_id, "live_traffic", lt)

    if _enabled(toggles, "static"):
        st = {
            "location": loc_ctx,
            "state": state,
            "forecast_days": 30,
        }
        db.insert_raw_signal(location_id, "static", st)
        run_preprocessors(location_id, "static", st)

    if settings.dev_synthetic_signals:
        from dev_fixtures.synthetic_signals import inject_synthetic_signals
        inject_synthetic_signals(location_id)
