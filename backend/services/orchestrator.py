from __future__ import annotations

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
    if signal_type == "popular_times":
        process_popular_times_signal(raw_json, location_id)
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
        return

    result = fn(raw_json, location_id)
    if result:
        db.write_processed_signals(location_id, signal_type, result)
