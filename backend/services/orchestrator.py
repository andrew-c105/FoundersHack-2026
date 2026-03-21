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

    preprocessors: dict[str, PreprocessorFn] = {
        "ticketmaster": process_event_signal,
        "eventbrite": process_event_signal,
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
