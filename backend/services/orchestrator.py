from __future__ import annotations

import json
from typing import Any, Callable

import database as db
from preprocessors import (
    process_competitor_signal,
    process_event_signal,
    process_popular_times_signal,
    process_static_signal,
    process_transport_signal,
    process_weather_signal,
)

PreprocessorFn = Callable[[dict[str, Any], str], list[dict[str, Any]]]

EVENT_SIGNAL_TYPES = {"ticketmaster", "eventbrite"}


def _build_business_profile(location_id: str) -> dict[str, str]:
    """Build a business profile dict from the location row for the LLM filter."""
    loc = db.get_location(location_id)
    if not loc:
        return {
            "business_name": "",
            "business_type": "restaurant",
            "address": "",
        }
    return {
        "business_name": str(loc.get("business_name") or loc.get("address") or ""),
        "business_type": str(loc.get("business_type") or "restaurant"),
        "address": str(loc.get("address") or f"{loc.get('lat', '')},{loc.get('lng', '')}"),
    }


def run_preprocessors(location_id: str, signal_type: str, raw_json: dict[str, Any]) -> None:
    print(f"\n{'='*60}")
    print(f"[PREPROCESSOR] signal_type={signal_type!r}  location_id={location_id!r}")
    print(f"[PREPROCESSOR] raw_json input:")
    print(json.dumps(raw_json, indent=2, default=str)[:3000])  # cap huge payloads
    print(f"{'='*60}")

    if signal_type == "popular_times":
        process_popular_times_signal(raw_json, location_id)
        print(f"[PREPROCESSOR] popular_times: wrote baseline rows (no processed_signals output)")
        return

    # ── Event signals get the LLM relevance filter ────────────────
    if signal_type in EVENT_SIGNAL_TYPES:
        business_profile = _build_business_profile(location_id)
        result = process_event_signal(raw_json, location_id, business_profile=business_profile)
        print(f"\n[PREPROCESSOR] result ({len(result)} rows):")
        for i, row in enumerate(result[:10]):
            print(f"  [{i}] {json.dumps(row, default=str)}")
        if len(result) > 10:
            print(f"  ... and {len(result) - 10} more rows")
        print(f"[PREPROCESSOR] END signal_type={signal_type!r}\n")
        if result:
            db.write_processed_signals(location_id, signal_type, result)
        return

    # ── All other signal types (unchanged) ────────────────────────
    preprocessors: dict[str, PreprocessorFn] = {
        "open_meteo": process_weather_signal,
        "google_places": process_competitor_signal,
        "transport_nsw": process_transport_signal,
        "live_traffic": process_transport_signal,
        "static": process_static_signal,
    }

    fn = preprocessors.get(signal_type)
    if fn is None:
        print(f"[PREPROCESSOR] WARNING: no preprocessor registered for signal_type={signal_type!r}")
        return

    result = fn(raw_json, location_id)
    print(f"\n[PREPROCESSOR] result ({len(result)} rows):")
    for i, row in enumerate(result[:10]):   # show up to first 10 rows
        print(f"  [{i}] {json.dumps(row, default=str)}")
    if len(result) > 10:
        print(f"  ... and {len(result) - 10} more rows")
    print(f"[PREPROCESSOR] END signal_type={signal_type!r}\n")

    if result:
        db.write_processed_signals(location_id, signal_type, result)
